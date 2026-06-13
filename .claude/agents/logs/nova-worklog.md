# Nova — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + LLMService (Ollama/OpenAI)

---

## Current State
*Last updated: 2026-06-13 · C36 committed*

**Last completed:** C36 `ingestion-pgvector-write-integration` — committed 2026-06-13 (c18a826)
**Currently active:** none
**Blocked by:** none

Tool usage: reads=14, writes=10, total=53 (across two invocations, both hit the 25-cap)
Note: counts are Nova's agent invocations only. Orchestrator applied a few additional direct
fixes post-session (see Session 2 corrections).

**Open Handoffs — Inbound:**
- ← Rex (C24): validated provider settings, dependencies, and one 768-dimensional
  embedding profile. ✅ actioned
- ← Rex (C26): `policy_documents`/`policy_chunks` hardened — status lifecycle, profile/provenance
  fields, ready-state trigger requiring all chunk embeddings non-null. ✅ actioned

**Open Handoffs — Outbound:**
- → Nova (C29): retrieval may assume deterministic chunk indexes and page/section metadata
  produced by `chunk_blocks()` in `backend/app/services/ingestion.py`. ✅ recorded in project-state.json
- → Rex (C28): create/resolve the `policy_documents` row and call the frozen
  `ingest_document()` contract; the service owns `processing -> ready|failed`. ✅ recorded in project-state.json
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
| 2 | C27 `document-ingestion` | committed 2026-06-10 (4323405) | Structure-first then token-bounded chunking (450/600/60 overlap) at whole-`ExtractedBlock` granularity; per-document `pg_advisory_xact_lock` serializes concurrent ingestion; failure path deletes partial chunks and marks `status='failed'` with sanitized error |
| 3 | C36 `ingestion-pgvector-write-integration` | committed 2026-06-13 (c18a826) | Replaced the skipped `TestIngestDocumentIntegration` placeholder with a real-DB `TestIngestDocumentPgvectorWrite` test (transaction-rollback fixture matching C35); proves `ingest_document()` writes 768-dim embeddings and chunk provenance matching `chunk_blocks()` |

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

---

## Session 2 — C27 `document-ingestion` · 2026-06-10

**Assigned:** Nova
**Status:** committed 2026-06-10 (4323405)
**Tool usage (Nova):** invocation A reads=10, writes=1, total=26 (hit cap, implementation only);
invocation B reads=4, writes=9, total=27 (hit cap, fixtures+tests+1 bugfix). Combined: reads=14, writes=10, total=53.
**Orchestrator corrections:** small fixes after both invocations (see below) — not Nova's work.

### What was built

Replaced the C16 stub `backend/app/services/ingestion.py` with a full pipeline:

- **Errors:** `IngestionError` and subclasses — `UnsupportedContentTypeError`, `EmptyDocumentError`,
  `EncryptedDocumentError`, `CorruptDocumentError`, `ImageOnlyDocumentError`, `InvalidEncodingError`.
- **Data types:** `ExtractedBlock`, `ExtractedDocument`, `Chunk`, `IngestResult` (frozen dataclasses).
- **Extractors:** PDF (PyMuPDF — rejects encrypted/image-only/empty), DOCX (python-docx —
  headings become section provenance, tables flattened to `"cell | cell"` rows, OLE-CFB
  magic-byte check for encrypted files), TXT/MD (strict UTF-8, `#` headings → section).
- **Normalization:** NFC unicode + whitespace collapse, paragraph/line structure preserved.
- **`chunk_blocks()`:** structure-first then `tiktoken` (`cl100k_base`) token-bounded
  chunking — target 450, hard cap 600, 60-token overlap within the same section only,
  deterministic, sequential `chunk_index`. Oversized single blocks are pre-split at the
  hard cap. Overlap operates at whole-`ExtractedBlock` granularity — if every block in a
  section exceeds the 60-token overlap budget, no overlap occurs for that boundary (by
  design; no sub-block overlap is attempted).
- **`ingest_document()`:** per-document `pg_advisory_xact_lock` (key derived from
  `sha256(document_id)`), CPU-heavy extraction/chunking via `asyncio.to_thread`, batched
  embeddings via `EmbeddingService.embed_documents()`, atomic replace-chunks +
  `chunk_count` + `status='ready'` + embedding profile fields in one transaction. On any
  exception: rollback, re-acquire lock, delete partial chunks, set `status='failed'` with
  a sanitized `error_message`, return `IngestResult` (never raises to the caller).

**Tests (Nova):** `backend/tests/services/test_ingestion.py` — 31 tests (after orchestrator
additions, see below) covering PDF/DOCX/TXT/MD extraction (headings, pages, tables, Unicode),
empty/encrypted/corrupt/image-only/invalid-UTF-8/unsupported-type rejections, chunking
(hard cap, overlap, determinism, sequential indices, section boundaries, metadata), and
`ingest_document` orchestration (success, empty doc, embedding-count mismatch, row-not-found,
idempotent retry). One opt-in `TestIngestDocumentIntegration` class is gated by
`MANIFESTO_DB_INTEGRATION_TESTS` (currently a stub — see Open Issue above).

**Fixtures:** `backend/tests/fixtures/documents/` — `sample.txt`, `sample.md` (static),
`sample.pdf`, `sample.docx`, `encrypted.pdf`, `encrypted.docx`, `corrupt.docx`,
`image_only.pdf` (generated by committed `make_fixtures.py`).

### Nova correction (within Session 2, invocation B)

1. **Encrypted DOCX detection bug** — `_extract_docx` originally caught a generic exception
   and string-matched `"encrypt"`/`"password"` in the message, but `python-docx` raises
   `PackageNotFoundError` for real encrypted OOXML (OLE-CFB, not a valid zip), which mapped
   to `CorruptDocumentError` instead of `EncryptedDocumentError`. Nova added an OLE-CFB
   magic-byte (`D0 CF 11 E0 A1 B1 1A E1`) check before attempting to open as zip. Verified
   against a real OLE-CFB fixture (`encrypted.docx`).

### Orchestrator corrections (2026-06-10 — NOT Nova's work)

2. **One-line test assertion fix** — `test_document_row_not_found_marks_failed` expected
   the generic sanitized message, but `IngestionError("Document row not found during
   publish.")` is itself an `IngestionError` subclass, so `_sanitize_error` returns the
   message verbatim. Corrected the expected string. (Nova had identified and reported this
   exact fix but hit the tool cap before applying it.)
3. **`test_overlap_within_same_section` fixed** — original test used 15 blocks of ~73
   tokens each; since each block alone exceeds the 60-token overlap budget, the
   whole-block-granularity overlap algorithm correctly produces zero overlap, failing the
   test's assumption. Rewrote the test with 80 small blocks (~7 tokens each) so the
   overlap tail can span whole blocks, matching the documented chunking design.
4. **Added `test_advisory_lock_acquired`** — the C27 test gate requires "concurrent lock
   path" coverage; no test asserted `pg_advisory_xact_lock` was actually issued. Added a
   test asserting the lock SQL appears in `db.execute.await_args_list`.
5. **`backend/DOMAIN_MAP.md` line-ending fix** — `prepare_agent_delegation.py`'s graph
   refresh wrote two new rows with CRLF into an LF file, tripping `git diff --check`.
   Normalized the whole file to LF.

Full suite after corrections: `pytest backend/tests/services/test_ingestion.py -q` →
**31 passed, 1 skipped**. Full backend suite: **106 passed, 1 skipped, 7 errors** — the 7
errors are pre-existing `tests/models/test_policy_storage.py` DB-connection failures from
C26 (OI-08, host port 5432 conflict), unrelated to this commit.

### Acceptance criteria

- [x] A fixture of each supported type reaches `ready` with deterministic chunks (verified
  via unit tests with `FakeEmbeddingService`)
- [x] No partial chunk set is visible after any injected failure
- [x] Duplicate/retried ingestion is idempotent (delete-then-replace, identical chunk content)
- [x] Unit tests use fake embeddings (done); one opt-in DB integration test verifies pgvector
  insertion and status transitions — completed in C36 (OI-08 resolved by C34's
  docker compose test runner)

---

## Session 3 — C36 `ingestion-pgvector-write-integration` · 2026-06-13

**Executor:** Claude (direct, per Eran's approval)
**Status:** committed 2026-06-13 (c18a826)
**Tool usage (orchestrator):** 0 agent calls

### What was built

Replaced the skipped `TestIngestDocumentIntegration` placeholder in
`backend/tests/services/test_ingestion.py` with `TestIngestDocumentPgvectorWrite`, a real
PostgreSQL + pgvector test using a transaction-rollback `db_session` fixture (matches
C35's `test_policy_storage.py` pattern; reads `DATABASE_URL` with a localhost fallback).

The test creates a `PolicyDocument` row (status='processing', embedding profile = 768
dims), runs `ingest_document()` with a `FakeEmbeddingService(dimensions=768)`, and
asserts:
- `result.status == "ready"`, `chunk_count > 0`
- persisted `policy_chunks` rows match `chunk_blocks(extract_document(...))`'s
  `chunk_index`, `page_number`, and `section` order/provenance
- every persisted `embedding` is a 768-dim vector (matches the `Vector(768)` column)
- `policy_documents.status == "ready"` and `chunk_count` matches after refresh

### Verification

`docker compose run --rm backend uv run pytest tests/services/test_ingestion.py -k pgvector_write -q`
→ **1 passed**. Full file: `tests/services/test_ingestion.py` → **32 passed**.
verify_constraints all_pass (--execution claude-direct): files=1/4, diff_lines=85/350.
No gate wave at C36 (next wave at C40).

---

## Session 4 — C37 `ingestion-status-transaction-integration` · 2026-06-13

**Executor:** Claude (direct, per Eran's approval)
**Status:** pending approval
**Tool usage (orchestrator):** 0 agent calls

### What was built

Added `TestIngestDocumentTransactionIntegration` to
`backend/tests/services/test_ingestion.py`, using the C36 transaction-rollback
`db_session` fixture, with two real-DB tests:

- `test_successful_ingestion_commits_ready_state_with_chunk_count` — creates a
  `PolicyDocument` row (status='processing', 768-dim profile), runs `ingest_document()`
  with `FakeEmbeddingService(dimensions=768)`, and asserts `result.status == "ready"`,
  `chunk_count > 0`, `error_message is None`, and after refresh
  `policy_documents.status == "ready"` with `chunk_count` matching the persisted
  `policy_chunks` row count.
- `test_failed_publish_rolls_back_with_no_partial_chunks` — calls `ingest_document()`
  with a `document_id` that has no corresponding `policy_documents` row, so the publish
  `UPDATE ... WHERE id=:id` returns `rowcount == 0` and raises `IngestionError("Document
  row not found during publish.")`. Asserts `result.status == "failed"`,
  `chunk_count == 0`, `error_message == "Document row not found during publish."`, and
  that no `policy_chunks` rows exist for that document id — confirming the chunks added
  to the session before the failure were rolled back, not partially persisted.

### Verification

`docker compose run --rm backend uv run pytest tests/services/test_ingestion.py -k transaction -q`
→ **2 passed**. Full file: `tests/services/test_ingestion.py` → **34 passed**.
verify_constraints all_pass (--execution claude-direct): files=1/4, diff_lines=84/350.
No gate wave at C37 (next wave at C40).
