# Commit 25 — `llm-service-impl` · Nova

**Phase:** 2A — Provider Foundation
**Assignee:** Nova (AI/ML Engineer)
**Depends on:** C24 (llm-runtime-config)

**Viktor + Sage wave runs on this commit (C25 is the 25th commit; Sage is triggered by external API calls and secrets).**

---

## context

```
tier0:
  - .claude/agents/ai-engineer.md (Current State header only — first 50 lines)

tier1:
  - backend/app/services/llm.py     # C16 stub to replace
  - backend/app/core/config.py      # C24 provider/profile settings
  - backend/pyproject.toml          # available provider clients

tier2:
  - manifesto-spec.md (§5 LLM Provider Abstraction)

forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/models/
  - backend/alembic/
  - backend/app/core/

estimated_reads: 4
estimated_edits: 2   # llm.py + focused tests
fits_single_agent: true
```

---

## What

Implement typed, async provider adapters for generation and a separate deployment-wide
embedding service. This supersedes C16's assumption that chat and embeddings must use the
same provider.

Nova does not edit configuration, dependencies, routes, models, or migrations.

---

## Files to Change

| File | Type | Description |
|---|---|---|
| `backend/app/services/llm.py` | edit | Implement typed async generation and embedding adapters |
| `backend/tests/services/test_llm.py` | new | Mocked provider transport and contract tests |

---

## Public Contract

```python
class LLMService:
    def __init__(self, provider: Literal["ollama", "openai"]) -> None: ...

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool = True,
    ) -> AsyncIterator[str]: ...


class EmbeddingService:
    @property
    def profile(self) -> EmbeddingProfile: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...
```

`EmbeddingProfile` contains provider, model, and dimensions. Ingestion and retrieval use
the same configured profile; the user's chat-provider choice never changes vector space.

Define provider-neutral exceptions for invalid configuration, authentication, timeout,
rate limit, unavailable model, and malformed response. Routes must not depend on SDK
exception classes.

## Implementation Requirements

- Reuse pooled async clients; expose an application-shutdown close hook.
- Use the OpenAI Responses streaming API and consume typed text-delta/error/completion
  events. Use the Ollama chat API and parse newline-delimited JSON incrementally.
- Validate every embedding's count, numeric values, and exact dimension before returning.
- Batch embedding requests within provider limits; preserve input order.
- Apply bounded exponential backoff with jitter only to idempotent embedding calls and to
  generation failures before the first output token. Never replay a partially emitted
  answer.
- Enforce connect/read/overall timeouts and cancellation. Never catch
  `asyncio.CancelledError` as an ordinary provider failure.
- Do not log API keys, full prompts, document text, or generated answers. Log provider,
  model, latency, request ID when available, token/character counts, and normalized error.
- `stream=False` still honors the iterator contract by yielding one complete text item.

---

## Test Gate

- Provider dispatch and exact request payloads.
- Fragmented OpenAI SSE and Ollama NDJSON frames.
- Empty deltas, provider error frames, timeout, cancellation, and malformed JSON.
- Retry occurs before first token but never after a token was yielded.
- Embedding batches preserve order and reject a dimension mismatch.
- Missing credentials/model produce a normalized configuration error.

Real-provider smoke tests are opt-in and skipped when credentials/models are unavailable.

---

## Done When

- [ ] Both chat providers stream without blocking the event loop
- [ ] The single embedding profile is 768-dimensional and independent of chat provider
- [ ] All mocked contract tests pass without network access
- [ ] C27 and C29 depend only on provider-neutral types

---

## Handoffs Out

→ Nova (C27/C29): use `EmbeddingService` for corpus/query vectors and `LLMService` only
for generation. Do not couple vectors to the conversation provider.

→ Rex (C30): route code handles normalized service events/exceptions, never provider SDK types.
