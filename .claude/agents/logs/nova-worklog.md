# Nova — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + LLMService (Ollama/OpenAI)

---

## Current State
*Last updated: 2026-06-09 · C25 committed*

**Last completed:** C25 `llm-service-impl` — committed 2026-06-09
**Currently active:** none
**Blocked by:** none

Tool usage: reads=8, writes=3, total=25
Note: counts are Nova's agent invocation only. Orchestrator applied ~9 additional direct fixes post-session (see Session 1 corrections).

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
| 1 | C25 `llm-service-impl` | committed 2026-06-09 | Separate LLMService (per-conversation) from EmbeddingService (deployment-wide 768-dim); `chat()` returns AsyncIterator via async generator pattern; retry before first token only |

---

## Session 1 — C25 `llm-service-impl` · 2026-06-09

**Assigned:** Nova
**Status:** committed 2026-06-09
**Tool usage (Nova):** reads=8, writes=3, total=25 (hit cap)
**Orchestrator corrections:** ~9 additional direct edits by Claude post-session — not Nova's work (see corrections section below)

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

**Tests (Nova):** `backend/tests/services/test_llm.py` — 45 tests covering all spec gate items.

### Nova corrections (at commit time)

1. **Syntax error** — two `last_exc = LLMError(...) from exc` assignment lines in `_ollama_chat` (invalid Python: `from` is only valid on `raise` statements). Orchestrator removed the `from exc` suffixes.
2. **Missing dev dependency** — `pytest-asyncio` was absent from `backend/pyproject.toml`. All async tests failed. Orchestrator added `pytest-asyncio>=0.23.0` to dev deps and `asyncio_mode = "auto"` to pytest.ini_options.
3. **Incomplete test mock** — `_CaptureCM` lacked `status_code = 200`. Orchestrator added the attribute.

### Orchestrator post-session corrections (2026-06-09 — NOT Nova's work)

The following fixes were applied directly by Claude in a separate correction pass after C25 committed. They are orchestrator work, not Nova's:

4. **SSE parser rewrite** — replaced line-by-line OpenAI SSE parser with a proper `_iter_sse_events()` async generator that handles `event:` control lines, multi-line `data:` fields, and blank-line event boundaries.
5. **total_timeout enforcement** — added wall-clock deadline tracking (`time.monotonic()` + `self._total_timeout`) to `_openai_chat`, `_ollama_chat`, and both embedding retry loops. Deadline checked before each retry and after each retry delay. `CancelledError` continues to propagate unmodified.
6. **Provider and model validation** — both `LLMService` and `EmbeddingService` now raise `LLMConfigError` for unknown providers and empty model names.
7. **Log sanitisation** — removed `raw_line` from the OpenAI SSE malformed-data log call and `error` (provider message) from the Ollama error-frame log call. No raw content appears in any log record.
8. **uv.lock regeneration** — `uv lock` run after pyproject.toml changes; `pytest-asyncio v1.4.0` now in lock file.
9. **Negative tests added** (54 total, up from 45): unknown provider rejection, empty model rejection, `total_timeout` expiry before retry, SSE log-sanitisation check, Ollama error-frame log-sanitisation check, realistic SSE frame regression (event: + data: + blank separators).
10. **context_metrics.py fix** — selected-file utilisation now falls back to agent self-report cross-matched against package `selected_paths` when hooks `selected_read_paths` is empty. C25 correctly reports 7/8 selected files used (87.5%).

### Acceptance criteria

- [x] Both chat providers stream without blocking the event loop
- [x] The single embedding profile is 768-dimensional and independent of chat provider
- [x] All mocked contract tests pass without network access (54/54 after corrections)
- [x] C27 and C29 depend only on provider-neutral types
- [x] SSE parser handles event:, multi-line data:, and blank-line separators
- [x] total_timeout enforced as overall deadline including retries
- [x] Unknown providers and empty models rejected with LLMConfigError
- [x] No raw SSE lines or provider messages in logs
- [x] uv.lock includes pytest-asyncio
