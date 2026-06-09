"""LLM service — typed async provider adapters for generation and embeddings.

Two separate concerns:
- LLMService: per-conversation chat-generation provider (Ollama or OpenAI).
- EmbeddingService: single deployment-wide corpus embedding profile (768-dim).

Provider SDKs are isolated here. All business services depend on provider-neutral types.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import httpx

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_VALID_PROVIDERS: frozenset[str] = frozenset({"ollama", "openai"})

# ---------------------------------------------------------------------------
# Provider-neutral exceptions
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Base class for all LLM/embedding service errors."""


class LLMConfigError(LLMError):
    """Invalid configuration: missing credentials, unknown model, etc."""


class LLMAuthError(LLMError):
    """Authentication failure (bad or missing API key)."""


class LLMTimeoutError(LLMError):
    """Provider did not respond within the configured timeout."""


class LLMRateLimitError(LLMError):
    """Provider rejected the request due to rate limiting."""


class LLMUnavailableError(LLMError):
    """Model or provider is unavailable (not loaded, 503, etc.)."""


class LLMMalformedResponseError(LLMError):
    """Provider returned a response that could not be parsed."""


class LLMEmbeddingDimensionError(LLMError):
    """Embedding vector has unexpected dimensionality."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChatMessage:
    """A single turn in a conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class EmbeddingProfile:
    """Deployment-wide corpus embedding configuration (immutable after startup)."""

    provider: Literal["ollama", "openai"]
    model: str
    dimensions: int


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

_JITTER_BASE = 0.5
_JITTER_CAP = 30.0


def _backoff_delay(attempt: int) -> float:
    """Return bounded exponential backoff with full jitter (attempt is 0-based)."""
    base = min(_JITTER_CAP, _JITTER_BASE * (2**attempt))
    return random.uniform(0.0, base)


# ---------------------------------------------------------------------------
# SSE parser
# ---------------------------------------------------------------------------


async def _iter_sse_events(
    response: httpx.Response,
    deadline: float,
) -> AsyncIterator[dict[str, Any]]:
    """Parse an SSE stream into JSON event dicts.

    Handles event: control lines, multi-line data: fields, and blank-line
    event boundaries. Raises LLMTimeoutError if the overall deadline is exceeded.
    Never logs raw line content.
    """
    data_lines: list[str] = []

    async for line in response.aiter_lines():
        if time.monotonic() >= deadline:
            raise LLMTimeoutError("Total timeout expired during streaming.")

        if not line:
            # Blank line = end of SSE event block
            if data_lines:
                raw = "\n".join(data_lines)
                data_lines = []
                if raw == "[DONE]":
                    return
                try:
                    yield json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise LLMMalformedResponseError(
                        "OpenAI returned malformed streaming data."
                    ) from exc
        elif line.startswith("data:"):
            val = line[5:]
            if val.startswith(" "):
                val = val[1:]
            data_lines.append(val)
        elif line.startswith(("event:", "id:", ":")):
            pass  # SSE control lines; event type comes from the JSON type field

    # Process final event if the stream ended without a trailing blank line
    if data_lines:
        raw = "\n".join(data_lines)
        if raw != "[DONE]":
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                raise LLMMalformedResponseError(
                    "OpenAI returned malformed streaming data."
                ) from exc


# ---------------------------------------------------------------------------
# LLMService — per-conversation chat generation
# ---------------------------------------------------------------------------


class LLMService:
    """Async chat-generation adapter for Ollama and OpenAI.

    One instance per conversation (provider is conversation-level, not deployment-level).
    Manages a pooled async HTTP client; call ``close()`` at application shutdown.
    """

    def __init__(
        self,
        provider: Literal["ollama", "openai"],
        *,
        openai_api_key: str = "",
        openai_chat_model: str = "gpt-4o-mini",
        ollama_base_url: str = "http://ollama:11434",
        ollama_chat_model: str = "llama3.2",
        connect_timeout: float = 5.0,
        read_timeout: float = 60.0,
        total_timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        if provider not in _VALID_PROVIDERS:
            raise LLMConfigError(
                f"Unknown LLM provider {provider!r}. Must be 'ollama' or 'openai'."
            )
        if provider == "openai":
            if not openai_api_key:
                raise LLMConfigError(
                    "OPENAI_API_KEY is required when provider='openai'."
                )
            if not openai_chat_model:
                raise LLMConfigError(
                    "openai_chat_model must not be empty when provider='openai'."
                )
        elif provider == "ollama":
            if not ollama_chat_model:
                raise LLMConfigError(
                    "ollama_chat_model must not be empty when provider='ollama'."
                )

        self.provider = provider
        self._openai_api_key = openai_api_key
        self._openai_chat_model = openai_chat_model
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._ollama_chat_model = ollama_chat_model
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._total_timeout = total_timeout
        self._max_retries = max_retries

        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=total_timeout,
            pool=total_timeout,
        )
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Release the pooled HTTP client. Call at application shutdown."""
        await self._client.aclose()

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Stream (or buffer) a generation response.

        Yields text deltas. When ``stream=False`` yields one complete string.
        Never replays a partially emitted answer on retry.
        """
        if self.provider == "openai":
            return self._openai_chat(messages, stream=stream)
        return self._ollama_chat(messages, stream=stream)

    # ------------------------------------------------------------------
    # OpenAI implementation
    # ------------------------------------------------------------------

    async def _openai_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool,
    ) -> AsyncIterator[str]:
        """Use the OpenAI Responses streaming API (text-delta/error/completion events)."""
        payload: dict[str, Any] = {
            "model": self._openai_chat_model,
            "input": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self._openai_api_key}",
            "Content-Type": "application/json",
        }

        first_token_yielded = False
        last_exc: Exception | None = None
        deadline = time.monotonic() + self._total_timeout

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Total timeout expired.")
                delay = _backoff_delay(attempt - 1)
                logger.info(
                    "openai_chat_retry",
                    extra={"attempt": attempt, "delay_s": round(delay, 2)},
                )
                await asyncio.sleep(delay)
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Total timeout expired after retry delay.")

            t_start = time.monotonic()
            try:
                async with self._client.stream(
                    "POST",
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=payload,
                ) as response:
                    self._raise_for_openai_status(response.status_code)

                    accumulated: list[str] = []

                    async for event in _iter_sse_events(response, deadline):
                        event_type = event.get("type", "")

                        if event_type == "response.output_text.delta":
                            delta = event.get("delta", "")
                            if not delta:
                                continue
                            if stream:
                                first_token_yielded = True
                                yield delta
                            else:
                                accumulated.append(delta)

                        elif event_type == "response.failed":
                            error_info = event.get("response", {}).get("error", {})
                            code = error_info.get("code", "")
                            msg = error_info.get("message", "unknown error")
                            raise self._map_openai_error_code(code, msg)

                        elif event_type == "response.completed":
                            latency = time.monotonic() - t_start
                            logger.info(
                                "openai_chat_completed",
                                extra={
                                    "provider": "openai",
                                    "model": self._openai_chat_model,
                                    "latency_s": round(latency, 3),
                                },
                            )
                            if not stream and accumulated:
                                yield "".join(accumulated)
                            return

                return

            except asyncio.CancelledError:
                raise
            except (LLMAuthError, LLMConfigError, LLMUnavailableError):
                raise
            except (LLMRateLimitError, LLMTimeoutError, LLMMalformedResponseError, LLMError) as exc:
                last_exc = exc
                if attempt >= self._max_retries or first_token_yielded:
                    raise
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Total timeout expired.") from exc
            except httpx.TimeoutException as exc:
                last_exc = LLMTimeoutError(f"OpenAI request timed out: {exc}")
                if attempt >= self._max_retries or first_token_yielded or time.monotonic() >= deadline:
                    raise last_exc
            except httpx.HTTPStatusError as exc:
                self._raise_for_openai_status(exc.response.status_code)

        if last_exc is not None:
            raise last_exc

    @staticmethod
    def _raise_for_openai_status(status_code: int) -> None:
        """Map HTTP status codes to normalized LLM exceptions."""
        if status_code == 200:
            return
        if status_code == 401:
            raise LLMAuthError(f"OpenAI authentication failed (HTTP {status_code}).")
        if status_code == 429:
            raise LLMRateLimitError(f"OpenAI rate limit exceeded (HTTP {status_code}).")
        if status_code in (503, 529):
            raise LLMUnavailableError(f"OpenAI service unavailable (HTTP {status_code}).")
        if status_code >= 500:
            raise LLMUnavailableError(f"OpenAI server error (HTTP {status_code}).")
        raise LLMError(f"OpenAI returned unexpected status {status_code}.")

    @staticmethod
    def _map_openai_error_code(code: str, message: str) -> LLMError:
        if code in ("invalid_api_key", "no_such_api_key"):
            return LLMAuthError(f"OpenAI auth error: {message}")
        if code in ("rate_limit_exceeded",):
            return LLMRateLimitError(f"OpenAI rate limit: {message}")
        if code in ("model_not_found", "model_overloaded"):
            return LLMUnavailableError(f"OpenAI model unavailable: {message}")
        return LLMError(f"OpenAI error [{code}]: {message}")

    # ------------------------------------------------------------------
    # Ollama implementation
    # ------------------------------------------------------------------

    async def _ollama_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool,
    ) -> AsyncIterator[str]:
        """Use the Ollama chat API, parsing newline-delimited JSON incrementally."""
        payload: dict[str, Any] = {
            "model": self._ollama_chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }

        first_token_yielded = False
        last_exc: Exception | None = None
        deadline = time.monotonic() + self._total_timeout

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Total timeout expired.")
                delay = _backoff_delay(attempt - 1)
                logger.info(
                    "ollama_chat_retry",
                    extra={"attempt": attempt, "delay_s": round(delay, 2)},
                )
                await asyncio.sleep(delay)
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Total timeout expired after retry delay.")

            t_start = time.monotonic()
            try:
                async with self._client.stream(
                    "POST",
                    f"{self._ollama_base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code == 404:
                        raise LLMUnavailableError(
                            f"Ollama model '{self._ollama_chat_model}' not found."
                        )
                    if response.status_code != 200:
                        raise LLMError(
                            f"Ollama returned unexpected status {response.status_code}."
                        )

                    accumulated: list[str] = []

                    async for line in response.aiter_lines():
                        if time.monotonic() >= deadline:
                            raise LLMTimeoutError("Total timeout expired during streaming.")
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            frame = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise LLMMalformedResponseError(
                                "Ollama returned malformed streaming data."
                            ) from exc

                        if frame.get("error"):
                            raise LLMMalformedResponseError(
                                "Ollama chat service returned an error."
                            )

                        delta = frame.get("message", {}).get("content", "")
                        done = frame.get("done", False)

                        if delta:
                            if stream:
                                first_token_yielded = True
                                yield delta
                            else:
                                accumulated.append(delta)

                        if done:
                            latency = time.monotonic() - t_start
                            logger.info(
                                "ollama_chat_completed",
                                extra={
                                    "provider": "ollama",
                                    "model": self._ollama_chat_model,
                                    "latency_s": round(latency, 3),
                                },
                            )
                            if not stream and accumulated:
                                yield "".join(accumulated)
                            return

                return

            except asyncio.CancelledError:
                raise
            except (LLMUnavailableError, LLMConfigError):
                raise
            except (LLMMalformedResponseError, LLMTimeoutError, LLMError) as exc:
                last_exc = exc
                if attempt >= self._max_retries or first_token_yielded:
                    raise
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Total timeout expired.") from exc
            except httpx.TimeoutException as exc:
                last_exc = LLMTimeoutError(f"Ollama request timed out: {exc}")
                if attempt >= self._max_retries or first_token_yielded or time.monotonic() >= deadline:
                    raise last_exc
            except httpx.ConnectError as exc:
                last_exc = LLMUnavailableError(f"Ollama connection refused: {exc}")
                raise last_exc

        if last_exc is not None:
            raise last_exc


# ---------------------------------------------------------------------------
# EmbeddingService — deployment-wide corpus embedding
# ---------------------------------------------------------------------------


class EmbeddingService:
    """Single deployment-wide corpus embedding adapter.

    The embedding profile is fixed at startup. The chat provider never changes it.
    Changing the profile requires a schema migration and full corpus re-index.

    Manages a pooled async HTTP client; call ``close()`` at application shutdown.
    """

    # OpenAI batch limit; Ollama has no hard limit but we cap for memory safety
    _OPENAI_BATCH_SIZE = 2048
    _OLLAMA_BATCH_SIZE = 64

    def __init__(
        self,
        *,
        provider: Literal["ollama", "openai"],
        model: str,
        dimensions: int,
        openai_api_key: str = "",
        ollama_base_url: str = "http://ollama:11434",
        connect_timeout: float = 5.0,
        read_timeout: float = 60.0,
        total_timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        if provider not in _VALID_PROVIDERS:
            raise LLMConfigError(
                f"Unknown embedding provider {provider!r}. Must be 'ollama' or 'openai'."
            )
        if not model:
            raise LLMConfigError("model must not be empty.")
        if dimensions != 768:
            raise LLMConfigError(
                f"EmbeddingService requires dimensions=768 for Phase 2; got {dimensions}."
            )
        if provider == "openai" and not openai_api_key:
            raise LLMConfigError(
                "OPENAI_API_KEY is required when embedding provider='openai'."
            )

        self._profile = EmbeddingProfile(
            provider=provider,
            model=model,
            dimensions=dimensions,
        )
        self._openai_api_key = openai_api_key
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._max_retries = max_retries
        self._total_timeout = total_timeout

        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=total_timeout,
            pool=total_timeout,
        )
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def profile(self) -> EmbeddingProfile:
        """Return the immutable deployment-wide embedding profile."""
        return self._profile

    async def close(self) -> None:
        """Release the pooled HTTP client. Call at application shutdown."""
        await self._client.aclose()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a sequence of document texts. Batches internally; preserves input order."""
        if not texts:
            return []
        if self._profile.provider == "openai":
            return await self._openai_embed_batched(list(texts))
        return await self._ollama_embed_batched(list(texts))

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        results = await self.embed_documents([text])
        return results[0]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_embeddings(
        self, embeddings: list[list[float]], expected_count: int
    ) -> list[list[float]]:
        """Validate count, numeric values, and exact dimension for every vector."""
        if len(embeddings) != expected_count:
            raise LLMMalformedResponseError(
                f"Expected {expected_count} embeddings, got {len(embeddings)}."
            )
        for i, vec in enumerate(embeddings):
            if len(vec) != self._profile.dimensions:
                raise LLMEmbeddingDimensionError(
                    f"Vector[{i}] has dimension {len(vec)}, "
                    f"expected {self._profile.dimensions}."
                )
            for j, val in enumerate(vec):
                if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                    raise LLMMalformedResponseError(
                        f"Vector[{i}][{j}] is not a finite number: {val!r}."
                    )
        return embeddings

    # ------------------------------------------------------------------
    # OpenAI embedding implementation
    # ------------------------------------------------------------------

    async def _openai_embed_batched(self, texts: list[str]) -> list[list[float]]:
        """Batch texts, embed each batch, re-assemble in input order."""
        results: list[list[float]] = []
        batch_size = self._OPENAI_BATCH_SIZE
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            batch_vecs = await self._openai_embed_batch_with_retry(batch)
            results.extend(batch_vecs)
        return results

    async def _openai_embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_exc: Exception | None = None
        deadline = time.monotonic() + self._total_timeout
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Embedding total timeout expired.")
                delay = _backoff_delay(attempt - 1)
                logger.info(
                    "openai_embed_retry",
                    extra={"attempt": attempt, "delay_s": round(delay, 2)},
                )
                await asyncio.sleep(delay)
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Embedding total timeout expired after retry delay.")
            try:
                return await self._openai_embed_batch(texts)
            except asyncio.CancelledError:
                raise
            except (LLMAuthError, LLMConfigError, LLMEmbeddingDimensionError):
                raise
            except (LLMRateLimitError, LLMTimeoutError, LLMUnavailableError, LLMMalformedResponseError) as exc:
                last_exc = exc
                if attempt >= self._max_retries:
                    raise
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Embedding total timeout expired.") from exc
        raise last_exc  # type: ignore[misc]

    async def _openai_embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": self._profile.model,
            "input": texts,
            "dimensions": self._profile.dimensions,
            "encoding_format": "float",
        }
        headers = {
            "Authorization": f"Bearer {self._openai_api_key}",
            "Content-Type": "application/json",
        }

        t_start = time.monotonic()
        try:
            response = await self._client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI embedding request timed out: {exc}") from exc

        self._raise_for_openai_embed_status(response.status_code)

        try:
            body = response.json()
        except Exception as exc:
            raise LLMMalformedResponseError(
                f"OpenAI embedding response is not valid JSON: {exc}"
            ) from exc

        data = body.get("data")
        if not isinstance(data, list):
            logger.error(
                "openai_embed_malformed_response",
                extra={"body_keys": list(body.keys()) if isinstance(body, dict) else None},
            )
            raise LLMMalformedResponseError(
                "OpenAI embedding returned a malformed response."
            )

        # data is ordered by index field
        try:
            ordered = sorted(data, key=lambda x: x["index"])
            raw = [item["embedding"] for item in ordered]
        except (KeyError, TypeError) as exc:
            raise LLMMalformedResponseError(
                f"OpenAI embedding response malformed: {exc}"
            ) from exc

        validated = self._validate_embeddings(raw, len(texts))
        latency = time.monotonic() - t_start
        logger.info(
            "openai_embed_completed",
            extra={
                "provider": "openai",
                "model": self._profile.model,
                "count": len(texts),
                "latency_s": round(latency, 3),
            },
        )
        return validated

    @staticmethod
    def _raise_for_openai_embed_status(status_code: int) -> None:
        if status_code == 200:
            return
        if status_code == 401:
            raise LLMAuthError(f"OpenAI embedding authentication failed (HTTP {status_code}).")
        if status_code == 429:
            raise LLMRateLimitError(f"OpenAI embedding rate limit exceeded (HTTP {status_code}).")
        if status_code in (503, 529):
            raise LLMUnavailableError(f"OpenAI embedding service unavailable (HTTP {status_code}).")
        if status_code >= 500:
            raise LLMUnavailableError(f"OpenAI embedding server error (HTTP {status_code}).")
        raise LLMError(f"OpenAI embedding returned unexpected status {status_code}.")

    # ------------------------------------------------------------------
    # Ollama embedding implementation
    # ------------------------------------------------------------------

    async def _ollama_embed_batched(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        batch_size = self._OLLAMA_BATCH_SIZE
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            batch_vecs = await self._ollama_embed_batch_with_retry(batch)
            results.extend(batch_vecs)
        return results

    async def _ollama_embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_exc: Exception | None = None
        deadline = time.monotonic() + self._total_timeout
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Embedding total timeout expired.")
                delay = _backoff_delay(attempt - 1)
                logger.info(
                    "ollama_embed_retry",
                    extra={"attempt": attempt, "delay_s": round(delay, 2)},
                )
                await asyncio.sleep(delay)
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Embedding total timeout expired after retry delay.")
            try:
                return await self._ollama_embed_batch(texts)
            except asyncio.CancelledError:
                raise
            except (LLMUnavailableError, LLMConfigError, LLMEmbeddingDimensionError):
                raise
            except (LLMTimeoutError, LLMMalformedResponseError, LLMError) as exc:
                last_exc = exc
                if attempt >= self._max_retries:
                    raise
                if time.monotonic() >= deadline:
                    raise LLMTimeoutError("Embedding total timeout expired.") from exc
        raise last_exc  # type: ignore[misc]

    async def _ollama_embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": self._profile.model,
            "input": texts,
        }

        t_start = time.monotonic()
        try:
            response = await self._client.post(
                f"{self._ollama_base_url}/api/embed",
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Ollama embedding request timed out: {exc}") from exc
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(f"Ollama connection refused: {exc}") from exc

        if response.status_code == 404:
            raise LLMUnavailableError(
                f"Ollama model '{self._profile.model}' not found (HTTP 404)."
            )
        if response.status_code != 200:
            raise LLMError(
                f"Ollama embedding returned unexpected status {response.status_code}."
            )

        try:
            body = response.json()
        except Exception as exc:
            raise LLMMalformedResponseError(
                f"Ollama embedding response is not valid JSON: {exc}"
            ) from exc

        raw = body.get("embeddings")
        if not isinstance(raw, list):
            logger.error(
                "ollama_embed_malformed_response",
                extra={"body_keys": list(body.keys()) if isinstance(body, dict) else None},
            )
            raise LLMMalformedResponseError(
                "Ollama embedding returned a malformed response."
            )

        validated = self._validate_embeddings(raw, len(texts))
        latency = time.monotonic() - t_start
        logger.info(
            "ollama_embed_completed",
            extra={
                "provider": "ollama",
                "model": self._profile.model,
                "count": len(texts),
                "latency_s": round(latency, 3),
            },
        )
        return validated
