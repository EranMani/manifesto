# Commit 05 — `database-session` · Rex

**Phase:** 1B — Backend Core
**Assignee:** Rex (Backend)
**Depends on:** C04 (config-and-security)

---

## What

Wire up the async SQLAlchemy engine and session factory. No models yet.
Goal: the app connects to PostgreSQL on startup and `get_db` yields a session.

**Viktor wave runs on this commit (C05 is the 5th commit).**

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/core/database.py` | new | Async engine, async session factory, get_db dependency |

---

## core/database.py

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

---

## Done When

- [ ] `from app.core.database import engine, get_db, Base` imports without error
- [ ] App starts without DB connection error when Postgres is running
- [ ] `get_db` is a valid FastAPI dependency (yields AsyncSession)

---

## Handoffs Out

→ Rex (C06): `Base` from `database.py` is the declarative base — all models must inherit from it.
→ Rex (C07): `engine` is the async engine Alembic's `env.py` will use for `run_async_migrations`.
