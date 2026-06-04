# Commit 07 — `alembic-migration` · Rex

**Phase:** 1B — Backend Core
**Assignee:** Rex (Backend)
**Depends on:** C06 (sqlalchemy-models)

---

## What

Initialize Alembic and generate the initial migration from the SQLAlchemy models.
`alembic upgrade head` must run clean against a live Postgres instance.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/alembic.ini` | new | Alembic config, sqlalchemy.url placeholder |
| `backend/alembic/env.py` | new | Async migration runner, imports Base.metadata |
| `backend/alembic/script.py.mako` | new | Standard migration template |
| `backend/alembic/versions/0001_initial.py` | new | Generated migration — all tables |

---

## alembic/env.py Key Pattern

Must use async engine for migrations:

```python
from app.core.database import Base, engine
from app.models import *  # noqa — populates Base.metadata

def run_migrations_online():
    connectable = engine
    # use AsyncEngine.connect() with run_sync
```

Standard pattern: `async_engine_from_config` or direct engine import. Use whichever is cleaner with SQLAlchemy 2 async.

---

## Migration Must Include

- `CREATE EXTENSION IF NOT EXISTS vector;` before table creation (pgvector)
- All 9 tables in dependency order (users → vendors → categories → shipments → products → conversations → messages → policy_documents → policy_chunks)
- `IVFFlat` index on `policy_chunks.embedding`
- Index on `messages(conversation_id, created_at)`
- CHECK constraints on role, chat_type, llm_provider, role (messages)

---

## Done When

- [ ] `alembic upgrade head` runs against live Postgres without errors
- [ ] All 9 tables exist in the database after migration
- [ ] `alembic downgrade -1` works cleanly (rollback is safe)
- [ ] `alembic current` shows `0001_initial (head)`

---

## Handoffs Out

→ Rex (C08): Database schema is live. `seed.py` can now INSERT into `users` table.
