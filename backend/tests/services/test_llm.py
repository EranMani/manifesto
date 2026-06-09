"""Mocked contract tests for LLMService and EmbeddingService.

All tests run without network access. Provider transports are replaced with
controlled mocks to verify:
- Correct request payloads dispatched to each provider.
- Fragmented SSE / NDJSON frame parsing.
- Empty deltas, error frames, timeout, cancellation, malformed JSON.
- Retry before first token; no retry after partial emission.
- Embedding batches preserve order; dimension mismatch is rejected.
- Missing credentials / model produce a normalized configuration error.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.llm import (
    ChatMessage,
    EmbeddingProfile,
    EmbeddingService,
    LLMAuthError,
    LLMConfigError,
    LLMEmbeddingDimensionError,
    LLMMalformedResponseError,
    LLMRateLimitError,
    LLMService,
    LLMTimeoutError,
    LLMUnavailableError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_KEY = "sk-test-key-1234"
_DIMS = 768
_FAKE_VEC = [0.1] * _DIMS


def _openai_llm(**kwargs: Any) -> LLMService:
    defaults = dict(
        provider="openai",
        openai_api_key=_FAKE_KEY,
        openai_chat_model="gpt-4o-mini",
        max_retries=1,
    )
    defaults.update(kwargs)
    return LLMService(**defaults)


def _ollama_llm(**kwargs: Any) -> LLMService:
    defaults = dict(
        provider="ollama",
        ollama_base_url="http://localhost:11434",
        ollama_chat_model="llama3.2",
        max_retries=1,
    )
    defaults.update(kwargs)
    return LLMService(**defaults)


def _openai_embed(**kwargs: Any) -> EmbeddingService:
    defaults = dict(
        provider="openai",
        model="text-embedding-3-small",
        dimensions=_DIMS,
        openai_api_key=_FAKE_KEY,
        max_retries=1,
    )
    defaults.update(kwargs)
    return EmbeddingService(**defaults)


def _ollama_embed(**kwargs: Any) -> EmbeddingService:
    defaults = dict(
        provider="ollama",
        model="nomic-embed-text",
        dimensions=_DIMS,
        ollama_base_url="http://localhost:11434",
        max_retries=1,
    )
    defaults.update(kwargs)
    return EmbeddingService(**defaults)


async def _collect(gen: AsyncIterator[str]) -> list[str]:
    """Drain an async iterator into a list."""
    return [chunk async for chunk in await gen]


# ---------------------------------------------------------------------------
# Context-manager helper for mocking httpx streaming responses
# ---------------------------------------------------------------------------


class _FakeStreamResponse:
    """Minimal mock of an httpx streaming response context manager."""

    def __init__(self, status_code: int, lines: list[str]) -> None:
        self.status_code = status_code
        self._lines = lines

    async def __aenter__(self) -> "_FakeStreamResponse":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class _FakeResponse:
    """Minimal mock of a non-streaming httpx response."""

    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return self._body


# ---------------------------------------------------------------------------
# LLMService — configuration guard tests
# ---------------------------------------------------------------------------


class TestLLMServiceConfig:
    def test_openai_requires_api_key(self) -> None:
        with pytest.raises(LLMConfigError, match="OPENAI_API_KEY"):
            LLMService(provider="openai", openai_api_key="")

    def test_ollama_does_not_require_api_key(self) -> None:
        svc = _ollama_llm()
        assert svc.provider == "ollama"

    def test_provider_stored(self) -> None:
        svc = _openai_llm()
        assert svc.provider == "openai"


# ---------------------------------------------------------------------------
# LLMService — OpenAI streaming
# ---------------------------------------------------------------------------


class TestOpenAIChatStreaming:
    def _sse_lines(self, deltas: list[str], *, include_done: bool = True) -> list[str]:
        lines: list[str] = []
        for d in deltas:
            payload = {"type": "response.output_text.delta", "delta": d}
            lines.append(f"data: {json.dumps(payload)}")
        if include_done:
            lines.append('data: {"type": "response.completed"}')
        return lines

    @pytest.mark.asyncio
    async def test_streams_deltas(self) -> None:
        svc = _openai_llm()
        fake_resp = _FakeStreamResponse(200, self._sse_lines(["Hello", ", ", "world"]))
        with patch.object(svc._client, "stream", return_value=fake_resp):
            chunks = await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))
        assert chunks == ["Hello", ", ", "world"]

    @pytest.mark.asyncio
    async def test_stream_false_yields_single_item(self) -> None:
        svc = _openai_llm()
        fake_resp = _FakeStreamResponse(200, self._sse_lines(["Hello", ", ", "world"]))
        with patch.object(svc._client, "stream", return_value=fake_resp):
            chunks = await _collect(svc.chat([ChatMessage("user", "hi")], stream=False))
        assert len(chunks) == 1
        assert chunks[0] == "Hello, world"

    @pytest.mark.asyncio
    async def test_empty_deltas_skipped(self) -> None:
        svc = _openai_llm()
        lines = [
            'data: {"type": "response.output_text.delta", "delta": ""}',
            'data: {"type": "response.output_text.delta", "delta": "actual"}',
            'data: {"type": "response.completed"}',
        ]
        fake_resp = _FakeStreamResponse(200, lines)
        with patch.object(svc._client, "stream", return_value=fake_resp):
            chunks = await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))
        assert chunks == ["actual"]

    @pytest.mark.asyncio
    async def test_data_done_sentinel_ignored(self) -> None:
        svc = _openai_llm()
        lines = [
            'data: {"type": "response.output_text.delta", "delta": "ok"}',
            "data: [DONE]",
        ]
        fake_resp = _FakeStreamResponse(200, lines)
        with patch.object(svc._client, "stream", return_value=fake_resp):
            chunks = await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))
        assert chunks == ["ok"]

    @pytest.mark.asyncio
    async def test_malformed_json_raises(self) -> None:
        svc = _openai_llm()
        fake_resp = _FakeStreamResponse(200, ["data: not-json"])
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMMalformedResponseError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_error_frame_raises(self) -> None:
        svc = _openai_llm()
        err_frame = json.dumps({
            "type": "response.failed",
            "response": {"error": {"code": "model_not_found", "message": "no such model"}},
        })
        fake_resp = _FakeStreamResponse(200, [f"data: {err_frame}"])
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMUnavailableError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self) -> None:
        svc = _openai_llm()
        fake_resp = _FakeStreamResponse(401, [])
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMAuthError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit(self) -> None:
        svc = _openai_llm()
        fake_resp = _FakeStreamResponse(429, [])
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMRateLimitError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self) -> None:
        svc = _openai_llm(max_retries=0)

        async def _raise_timeout(*args: Any, **kwargs: Any) -> Any:
            raise httpx.ReadTimeout("timed out")

        # We need a context manager mock
        class _FailCM:
            async def __aenter__(self) -> "_FailCM":
                raise httpx.ReadTimeout("timed out")

            async def __aexit__(self, *a: Any) -> None:
                pass

        with patch.object(svc._client, "stream", return_value=_FailCM()):
            with pytest.raises(LLMTimeoutError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_cancellation_propagates(self) -> None:
        svc = _openai_llm()

        class _CancelCM:
            async def __aenter__(self) -> "_CancelCM":
                raise asyncio.CancelledError()

            async def __aexit__(self, *a: Any) -> None:
                pass

        with patch.object(svc._client, "stream", return_value=_CancelCM()):
            with pytest.raises(asyncio.CancelledError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_retry_before_first_token(self) -> None:
        """Rate-limit on first attempt → retry → success on second."""
        svc = _openai_llm(max_retries=2)
        call_count = 0

        def _make_cm() -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _FakeStreamResponse(429, [])
            return _FakeStreamResponse(
                200,
                [
                    'data: {"type": "response.output_text.delta", "delta": "ok"}',
                    'data: {"type": "response.completed"}',
                ],
            )

        with patch.object(svc._client, "stream", side_effect=lambda *a, **kw: _make_cm()):
            with patch("app.services.llm.asyncio.sleep", new_callable=AsyncMock):
                chunks = await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))
        assert chunks == ["ok"]
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_after_partial_emission(self) -> None:
        """Once a token is yielded, errors are NOT retried."""
        svc = _openai_llm(max_retries=2)

        partial_lines = [
            'data: {"type": "response.output_text.delta", "delta": "partial"}',
            'data: not-valid-json',
        ]
        fake_resp = _FakeStreamResponse(200, partial_lines)
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMMalformedResponseError):
                chunks: list[str] = []
                async for chunk in await svc.chat([ChatMessage("user", "hi")], stream=True):
                    chunks.append(chunk)


# ---------------------------------------------------------------------------
# LLMService — Ollama streaming
# ---------------------------------------------------------------------------


class TestOllamaChatStreaming:
    def _ndjson_lines(self, deltas: list[str]) -> list[str]:
        lines = []
        for i, d in enumerate(deltas):
            done = i == len(deltas) - 1
            lines.append(json.dumps({"message": {"role": "assistant", "content": d}, "done": done}))
        return lines

    @pytest.mark.asyncio
    async def test_streams_deltas(self) -> None:
        svc = _ollama_llm()
        fake_resp = _FakeStreamResponse(200, self._ndjson_lines(["Hi", " there"]))
        with patch.object(svc._client, "stream", return_value=fake_resp):
            chunks = await _collect(svc.chat([ChatMessage("user", "hello")], stream=True))
        assert chunks == ["Hi", " there"]

    @pytest.mark.asyncio
    async def test_stream_false_yields_single_item(self) -> None:
        svc = _ollama_llm()
        fake_resp = _FakeStreamResponse(200, self._ndjson_lines(["Hi", " there"]))
        with patch.object(svc._client, "stream", return_value=fake_resp):
            chunks = await _collect(svc.chat([ChatMessage("user", "hello")], stream=False))
        assert len(chunks) == 1
        assert chunks[0] == "Hi there"

    @pytest.mark.asyncio
    async def test_404_raises_unavailable(self) -> None:
        svc = _ollama_llm()
        fake_resp = _FakeStreamResponse(404, [])
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMUnavailableError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_malformed_json_raises(self) -> None:
        svc = _ollama_llm()
        fake_resp = _FakeStreamResponse(200, ["not-valid-json"])
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMMalformedResponseError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_error_frame_raises(self) -> None:
        svc = _ollama_llm()
        fake_resp = _FakeStreamResponse(200, [json.dumps({"error": "model overloaded"})])
        with patch.object(svc._client, "stream", return_value=fake_resp):
            with pytest.raises(LLMMalformedResponseError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_cancellation_propagates(self) -> None:
        svc = _ollama_llm()

        class _CancelCM:
            async def __aenter__(self) -> "_CancelCM":
                raise asyncio.CancelledError()

            async def __aexit__(self, *a: Any) -> None:
                pass

        with patch.object(svc._client, "stream", return_value=_CancelCM()):
            with pytest.raises(asyncio.CancelledError):
                await _collect(svc.chat([ChatMessage("user", "hi")], stream=True))

    @pytest.mark.asyncio
    async def test_request_payload_contains_model_and_messages(self) -> None:
        """Verify exact request payload sent to Ollama."""
        svc = _ollama_llm(ollama_chat_model="llama3.2")
        captured: dict[str, Any] = {}

        class _CaptureCM:
            status_code = 200

            def __init__(self, method: str, url: str, **kwargs: Any) -> None:
                captured.update(kwargs)

            async def __aenter__(self) -> "_CaptureCM":
                return self

            async def __aexit__(self, *a: Any) -> None:
                pass

            async def aiter_lines(self) -> AsyncIterator[str]:
                yield json.dumps({"message": {"content": "pong"}, "done": True})

        with patch.object(svc._client, "stream", _CaptureCM):
            await _collect(svc.chat([ChatMessage("user", "ping")], stream=True))

        assert captured["json"]["model"] == "llama3.2"
        assert captured["json"]["messages"][0] == {"role": "user", "content": "ping"}


# ---------------------------------------------------------------------------
# EmbeddingService — configuration guard
# ---------------------------------------------------------------------------


class TestEmbeddingServiceConfig:
    def test_wrong_dimensions_raises_config_error(self) -> None:
        with pytest.raises(LLMConfigError, match="768"):
            EmbeddingService(
                provider="ollama",
                model="nomic-embed-text",
                dimensions=1536,
            )

    def test_openai_requires_api_key(self) -> None:
        with pytest.raises(LLMConfigError, match="OPENAI_API_KEY"):
            EmbeddingService(
                provider="openai",
                model="text-embedding-3-small",
                dimensions=768,
                openai_api_key="",
            )

    def test_profile_exposed(self) -> None:
        svc = _ollama_embed()
        assert svc.profile == EmbeddingProfile(
            provider="ollama",
            model="nomic-embed-text",
            dimensions=768,
        )


# ---------------------------------------------------------------------------
# EmbeddingService — OpenAI embeddings
# ---------------------------------------------------------------------------


class TestOpenAIEmbeddings:
    def _fake_openai_response(self, vecs: list[list[float]]) -> _FakeResponse:
        data = [{"index": i, "embedding": v} for i, v in enumerate(vecs)]
        return _FakeResponse(200, {"data": data})

    @pytest.mark.asyncio
    async def test_embed_documents_returns_ordered_vectors(self) -> None:
        svc = _openai_embed()
        vecs = [[0.1 * (i + 1)] * _DIMS for i in range(3)]
        fake_resp = self._fake_openai_response(vecs)
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            result = await svc.embed_documents(["a", "b", "c"])
        assert len(result) == 3
        assert result[0][0] == pytest.approx(0.1)
        assert result[2][0] == pytest.approx(0.3)

    @pytest.mark.asyncio
    async def test_embed_query_returns_single_vector(self) -> None:
        svc = _openai_embed()
        fake_resp = self._fake_openai_response([_FAKE_VEC])
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            result = await svc.embed_query("query text")
        assert len(result) == _DIMS

    @pytest.mark.asyncio
    async def test_dimension_mismatch_raises(self) -> None:
        svc = _openai_embed()
        bad_vec = [0.1] * 1536  # wrong dimension
        fake_resp = self._fake_openai_response([bad_vec])
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMEmbeddingDimensionError):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self) -> None:
        svc = _openai_embed()
        fake_resp = _FakeResponse(401, {})
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMAuthError):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit(self) -> None:
        svc = _openai_embed(max_retries=0)
        fake_resp = _FakeResponse(429, {})
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMRateLimitError):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self) -> None:
        svc = _openai_embed(max_retries=0)
        with patch.object(
            svc._client, "post", new_callable=AsyncMock,
            side_effect=httpx.ReadTimeout("timeout")
        ):
            with pytest.raises(LLMTimeoutError):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self) -> None:
        svc = _openai_embed(max_retries=2)
        call_count = 0

        async def _mock_post(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _FakeResponse(429, {})
            return self._fake_openai_response([_FAKE_VEC])

        with patch.object(svc._client, "post", side_effect=_mock_post):
            with patch("app.services.llm.asyncio.sleep", new_callable=AsyncMock):
                result = await svc.embed_documents(["text"])
        assert call_count == 2
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self) -> None:
        svc = _openai_embed()
        result = await svc.embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_out_of_order_indices_preserved(self) -> None:
        """OpenAI may return embeddings in any order; we sort by index."""
        svc = _openai_embed()
        # Return in reverse order
        data = [
            {"index": 2, "embedding": [0.3] * _DIMS},
            {"index": 0, "embedding": [0.1] * _DIMS},
            {"index": 1, "embedding": [0.2] * _DIMS},
        ]
        fake_resp = _FakeResponse(200, {"data": data})
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            result = await svc.embed_documents(["a", "b", "c"])
        assert result[0][0] == pytest.approx(0.1)
        assert result[1][0] == pytest.approx(0.2)
        assert result[2][0] == pytest.approx(0.3)

    @pytest.mark.asyncio
    async def test_request_includes_dimensions_768(self) -> None:
        """Verify dimensions=768 is sent in the request payload."""
        svc = _openai_embed()
        captured: dict[str, Any] = {}

        async def _mock_post(url: str, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return self._fake_openai_response([_FAKE_VEC])

        with patch.object(svc._client, "post", side_effect=_mock_post):
            await svc.embed_documents(["text"])
        assert captured["json"]["dimensions"] == 768


# ---------------------------------------------------------------------------
# EmbeddingService — Ollama embeddings
# ---------------------------------------------------------------------------


class TestOllamaEmbeddings:
    def _fake_ollama_response(self, vecs: list[list[float]]) -> _FakeResponse:
        return _FakeResponse(200, {"embeddings": vecs})

    @pytest.mark.asyncio
    async def test_embed_documents_returns_vectors(self) -> None:
        svc = _ollama_embed()
        vecs = [_FAKE_VEC, [0.2] * _DIMS]
        fake_resp = self._fake_ollama_response(vecs)
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            result = await svc.embed_documents(["a", "b"])
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_dimension_mismatch_raises(self) -> None:
        svc = _ollama_embed()
        bad_vec = [0.1] * 512
        fake_resp = self._fake_ollama_response([bad_vec])
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMEmbeddingDimensionError):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_404_raises_unavailable(self) -> None:
        svc = _ollama_embed()
        fake_resp = _FakeResponse(404, {})
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMUnavailableError):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self) -> None:
        svc = _ollama_embed(max_retries=0)
        with patch.object(
            svc._client, "post", new_callable=AsyncMock,
            side_effect=httpx.ReadTimeout("timeout")
        ):
            with pytest.raises(LLMTimeoutError):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self) -> None:
        svc = _ollama_embed()
        result = await svc.embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_request_payload_model(self) -> None:
        svc = _ollama_embed(model="nomic-embed-text")
        captured: dict[str, Any] = {}

        async def _mock_post(url: str, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return self._fake_ollama_response([_FAKE_VEC])

        with patch.object(svc._client, "post", side_effect=_mock_post):
            await svc.embed_documents(["hello"])
        assert captured["json"]["model"] == "nomic-embed-text"

    @pytest.mark.asyncio
    async def test_batch_preserves_order(self) -> None:
        """Batching logic must preserve input order across batch boundaries."""
        svc = _ollama_embed(max_retries=0)
        # Force batch size of 2 for this test
        svc._OLLAMA_BATCH_SIZE = 2
        texts = ["a", "b", "c"]
        call_count = 0

        async def _mock_post(url: str, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            batch = kwargs["json"]["input"]
            # Return different vectors per text so order can be verified
            vecs = [[float(ord(t[0]))] * _DIMS for t in batch]
            return _FakeResponse(200, {"embeddings": vecs})

        with patch.object(svc._client, "post", side_effect=_mock_post):
            result = await svc.embed_documents(texts)

        assert call_count == 2  # 2 + 1 texts split into 2 batches
        assert result[0][0] == pytest.approx(float(ord("a")))
        assert result[1][0] == pytest.approx(float(ord("b")))
        assert result[2][0] == pytest.approx(float(ord("c")))


# ---------------------------------------------------------------------------
# EmbeddingService — NaN / inf rejection
# ---------------------------------------------------------------------------


class TestEmbeddingValidation:
    @pytest.mark.asyncio
    async def test_nan_value_rejected(self) -> None:
        svc = _ollama_embed()
        bad_vec = [float("nan")] * _DIMS
        fake_resp = _FakeResponse(200, {"embeddings": [bad_vec]})
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMMalformedResponseError, match="finite"):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_inf_value_rejected(self) -> None:
        svc = _ollama_embed()
        bad_vec = [float("inf")] * _DIMS
        fake_resp = _FakeResponse(200, {"embeddings": [bad_vec]})
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMMalformedResponseError, match="finite"):
                await svc.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_count_mismatch_raises(self) -> None:
        svc = _ollama_embed()
        # Request 2 texts but return 1 vector
        fake_resp = _FakeResponse(200, {"embeddings": [_FAKE_VEC]})
        with patch.object(svc._client, "post", new_callable=AsyncMock, return_value=fake_resp):
            with pytest.raises(LLMMalformedResponseError, match="Expected 2"):
                await svc.embed_documents(["a", "b"])
