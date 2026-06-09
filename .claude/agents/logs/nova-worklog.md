# Nova — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + LLMService (Ollama/OpenAI)

---

## Current State
*Last updated: 2026-06-09 · C25 complete — pending approval*

**Last completed:** C25 `llm-service-impl` — pending Eran's commit approval
**Currently active:** none
**Blocked by:** none

Tool usage: reads=8, writes=3, total=25

**Open Handoffs — Inbound:**
- ← Rex (C24): validated provider settings, dependencies, and one 768-dimensional
  embedding profile. ✅ actioned

**Open Handoffs — Outbound:**
- → Nova (C27/C29): Use `EmbeddingService.embed_documents()` / `embed_query()` for corpus/query vectors. Use `LLMService.chat()` only for generation. Profile is on `EmbeddingService.profile`.
- → Rex (C30): Catch only `LLMError` and subclasses in route handlers — never provider SDK exceptions.

**Key Interfaces I Will Own:**
- `backend/app/services/llm.py` — `LLMService` (Ollama + OpenAI abstraction)
- `backend/app/services/rag_policy.py` — retrieval + generation + citations for policy chat
- `backend/app/services/ingestion.py` — document chunking + embedding pipeline
- `backend/app/services/rag_logistics.py` — graph-plan-to-SQL pipeline (Phase 3)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 1 | C25 `llm-service-impl` | complete — pending approval | Separate LLMService (per-conversation) from EmbeddingService (deployment-wide 768-dim); `chat()` returns AsyncIterator via async generator pattern; retry before first token only |

---

## Session 1 — C25 `llm-service-impl` · 2026-06-09

**Assigned:** Nova
**Status:** complete — pending Eran's commit approval
**Tool usage:** reads=8, writes=3, total=25 (hit cap; orchestrator corrected two items)

### What was built

Replaced the C16 stub `backend/app/services/llm.py` with a full production implementation:

**Provider-neutral exceptions:** `LLMError`, `LLMConfigError`, `LLMAuthError`, `LLMTimeoutError`,
`LLMRateLimitError`, `LLMUnavailableError`, `LLMMalformedResponseError`, `LLMEmbeddingDimensionError`.

**Data types:** `ChatMessage(role, content)` and `EmbeddingProfile(provider, model, dimensions)` — both frozen dataclasses.

**LLMService** — per-conversation chat generation:
- OpenAI Responses API (SSE `text-delta`/`error`/`completed` events)
- Ollama NDJSON chat API
- Bounded exponential backoff with jitter; retry before first token only
- Pooled `httpx.AsyncClient`; `close()` shutdown hook

**EmbeddingService** — deployment-wide 768-dim corpus embedding:
- OpenAI `/v1/embeddings` with `dimensions=768`; Ollama `/api/embed`
- Batched (2048/64 per provider); input-order preserved (OpenAI sorts by `index`)
- Validates count, finite values, and exact dimension per vector
- Retry with backoff for idempotent calls; `close()` hook

**Tests:** `backend/tests/services/test_llm.py` — 45 tests covering all spec gate items (all pass).

### Orchestrator corrections

1. **Syntax error** — two `last_exc = LLMError(...) from exc` assignment lines in `_ollama_chat` (invalid Python: `from` is only valid on `raise` statements). Orchestrator removed the `from exc` suffixes at lines 413 and 417.
2. **Missing dev dependency** — `pytest-asyncio` was absent from `backend/pyproject.toml`. All 42 async tests failed with "async def functions are not natively supported." Orchestrator added `pytest-asyncio>=0.23.0` to dev deps and `asyncio_mode = "auto"` to pytest.ini_options.
3. **Incomplete test mock** — `_CaptureCM` in `test_request_payload_contains_model_and_messages` lacked `status_code = 200`, causing `AttributeError` when `llm.py` checked `response.status_code`. Orchestrator added the attribute. Implementation is correct; mock was incomplete.

### Acceptance criteria

- [x] Both chat providers stream without blocking the event loop
- [x] The single embedding profile is 768-dimensional and independent of chat provider
- [x] All mocked contract tests pass without network access (45/45)
- [x] C27 and C29 depend only on provider-neutral types
