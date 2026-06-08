# Commit 26 — `rag-storage-hardening` · Rex

**Phase:** 2A — RAG Storage Contract
**Assignee:** Rex (Backend)
**Depends on:** C24 (llm-runtime-config)

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header only — first 50 lines)

tier1:
  - backend/app/models/policy.py          # current policy schema
  - backend/alembic/versions/0001_initial.py  # applied C23 DDL
  - backend/alembic/env.py                # migration conventions

tier2:
  - commit-specs/PHASE-2-RAG-ARCHITECTURE-REVIEW.md

forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/services/

estimated_reads: 4
estimated_edits: 3   # migration, policy model, focused tests
fits_single_agent: true
```

---

## What

Make the existing policy schema safe for idempotent ingestion, operational recovery,
traceable retrieval, and later re-indexing before any production data is written.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `backend/alembic/versions/XXXX_rag_storage_hardening.py` | new | Add profile/status/provenance fields and replace vector index |
| `backend/app/models/policy.py` | edit | Match the additive schema |
| `backend/tests/models/test_policy_storage.py` | new | Migration constraints and index behavior |

Do not rewrite `0001_initial.py`; it is already applied.

---

## Schema Changes

Alter `policy_chunks.embedding` from `VECTOR(1536)` to `VECTOR(768)` before production
chunks exist. Drop/recreate the approximate index around the type change. The migration
must fail loudly if non-null legacy embeddings are present; silently truncating or casting
an existing vector space is forbidden.

`policy_documents` gains:

- `original_filename`, `content_type`, `byte_size`, `sha256`
- `status`: `pending | processing | ready | failed`
- `embedding_provider`, `embedding_model`, `embedding_dimensions`
- `error_message`, `chunk_count`, `updated_at`

`policy_chunks` gains:

- `token_count`
- `page_number` and `section` when extraction can supply them
- `metadata JSONB NOT NULL DEFAULT '{}'`
- generated `search_vector TSVECTOR` plus a GIN index for lexical retrieval
- unique `(document_id, chunk_index)`

Require non-null embeddings for ready chunks. Add a unique checksum/profile constraint
that makes retrying the same upload idempotent without preventing a future re-index under
a new embedding profile.

Replace the empty-corpus IVFFlat index with HNSW cosine indexing. HNSW can be built before
data exists and has a stronger speed/recall tradeoff for this evolving corpus. Keep index
parameters explicit and record that production tuning must use measured recall/latency.

---

## Transaction Rules

- A document row is created as `pending`.
- Ingestion transitions it to `processing`, then atomically publishes chunks and `ready`.
- Failure rolls back partial chunks and records a sanitized failure reason in a separate
  transaction.
- Retrieval filters to `status='ready'` and the active embedding profile.

---

## Done When

- [ ] Upgrade and downgrade work against a database at C23 head
- [ ] Duplicate upload/profile attempts resolve to the existing document or a conflict, never
  duplicate chunks.
- [ ] Unique chunk ordering and status constraints are enforced by PostgreSQL
- [ ] `EXPLAIN` can use the HNSW cosine index for a representative nearest-neighbor query

---

## Handoffs Out

→ Nova (C27/C29): retrieve only `ready` documents matching the active embedding profile;
the persisted vector column is `VECTOR(768)`.

→ Rex (C28/C31): API and persistence schemas may expose safe status/profile metadata but
never embeddings, chunk contents, or internal error details.
