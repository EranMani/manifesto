# Commit 23 — `pgvector-migration` · Rex

**Phase:** 2A — RAG Storage Foundation
**Assignee:** Rex (Backend)
**Depends on:** C22 (Phase 1 complete)

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header only — first 50 lines)

tier1:
  - backend/alembic/env.py            # migration config — confirm pattern for new migrations
  - backend/app/models/__init__.py    # confirm model registration pattern

tier2:
  - manifesto-spec.md (§4 Database Schema, lines ~150-170 — policy_documents/policy_chunks DDL)

forbidden:
  - frontend/
  - backend/app/api/        # no routes this commit
  - backend/app/services/   # Nova's domain — not touched this commit

estimated_reads: 3
estimated_edits: 3   # migration file, models/policy.py (new), models/__init__.py
fits_single_agent: true
```

---

## What

Enable the `pgvector` Postgres extension and create the storage layer for policy RAG:
`policy_documents` (uploaded source files) and `policy_chunks` (chunked text + embeddings).
This is pure schema/model work — no ingestion logic, no routes. Unblocks Nova's C24/C25.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `backend/alembic/versions/XXXX_pgvector_policy_tables.py` | new | `CREATE EXTENSION IF NOT EXISTS vector`, `policy_documents`, `policy_chunks` tables, ivfflat index |
| `backend/app/models/policy.py` | new | `PolicyDocument`, `PolicyChunk` SQLAlchemy models |
| `backend/app/models/__init__.py` | edit | register the two new models |

---

## Schema (per manifesto-spec.md §4)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE policy_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    file_path   TEXT,
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE policy_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES policy_documents(id) ON DELETE CASCADE,
    chunk_index INT,
    content     TEXT NOT NULL,
    embedding   VECTOR(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON policy_chunks USING ivfflat (embedding vector_cosine_ops);
```

**Embedding dimension note:** C23 shipped `VECTOR(1536)`. The architecture review later
standardized Phase 2 at 768 dimensions so local Ollama and OpenAI-with-dimensions=768
deployments use the same schema shape. C26 performs the additive migration before chunks
exist. The per-conversation generation provider does not alter the vector space.

---

## Done When

- [ ] Migration runs cleanly: `alembic upgrade head`
- [ ] `pgvector` extension is active (`SELECT * FROM pg_extension WHERE extname = 'vector'`)
- [ ] `policy_documents` and `policy_chunks` tables exist with correct columns, FKs, and ivfflat index
- [ ] `PolicyDocument` and `PolicyChunk` models import and map to the tables (`Base.metadata` reflects both)
- [ ] `alembic downgrade -1` cleanly reverses the migration

---

## Handoffs Out

→ Rex/Nova (C24-C27): the current column is `VECTOR(1536)`; C26 changes it to
`VECTOR(768)`. Use the single deployment-wide embedding profile configured in C24 for
both ingestion and query embeddings. Any provider/model change requires full re-index.
