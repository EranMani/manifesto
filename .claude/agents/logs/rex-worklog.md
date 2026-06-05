# Rex — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + React + Vite + Tailwind

---

## Current State
*Last updated: Commit 06 · 2026-06-05*

**Last completed:** Commit 06 `sqlalchemy-models` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- → Rex (C07): `models/__init__.py` imports all models — Alembic `env.py` will import `Base.metadata` from `app.core.database` and models from `app.models` to populate it
- → Rex (C08): `create_access_token` accepts `data: dict` — caller must pass `{"sub": str(user.id), "role": user.role}`
- → Rex (C09): `decode_token` raises HTTPException 401 — `get_current_user` dependency catches this naturally

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
- `backend/app/main.py` — FastAPI app entry point; `GET /` returns `{"status": "ok"}`; routers appended at bottom comment
- `backend/pyproject.toml` — all backend dependencies; uses `asyncpg` driver per Adam's C01 handoff
- Folder structure: `app/`, `app/api/`, `app/api/v1/`, `app/core/`, `app/models/`, `app/schemas/`, `app/services/`, `app/dependencies.py`
- Virtual environment at `backend/.venv` — created by `uv sync`

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | C02: python-skeleton | ✅ Done | Used exact pyproject.toml from spec; no deviations |
| 02 | C04: config-and-security | ✅ Done | Replaced passlib CryptContext with direct bcrypt calls due to version incompatibility |
| 03 | C06: sqlalchemy-models | ✅ Done | PolicyChunk IVFFlat index deferred to migration; `__table_args__` left as empty dict tuple |

---

## Session 01 — Commit 02: `python-skeleton`
*2026-06-04*

**Approach:** Phase 1 reads — confirmed backend/ contains only Dockerfile (from Adam's C01), confirmed logs dir exists. Phase 2 writes — created all 10 files per spec in exact order.

**Files created:**
- `backend/pyproject.toml` — exact content from spec
- `backend/app/__init__.py` — empty
- `backend/app/main.py` — FastAPI app with CORS middleware, structlog, health route
- `backend/app/api/__init__.py` — empty
- `backend/app/api/v1/__init__.py` — empty
- `backend/app/core/__init__.py` — empty
- `backend/app/models/__init__.py` — empty
- `backend/app/schemas/__init__.py` — empty
- `backend/app/services/__init__.py` — empty
- `backend/app/dependencies.py` — empty stub

**Test gate results:**
- `uv sync`: PASS — 43 packages installed, .venv created (uv 0.10.0, CPython 3.13.12)
- `from app.main import app` import: PASS — no errors, `app.title == "Manifesto"`
- `GET /` route registered and returns `{"status": "ok"}`: PASS (verified via import + route inspection)
- All `__init__.py` files exist: PASS — all 7 confirmed

**Decisions made:**
- No deviations from spec. `pyproject.toml` content copied verbatim. `main.py` structure copied verbatim.
- `allow_credentials=True` was NOT added to CORS middleware — spec did not include it, kept exact match.

**Issues encountered:**
- uv printed "Using CPython 3.13.12" to stderr — this is informational, not an error. System Python is 3.14.3 but uv resolved 3.13.12 for the venv. All packages installed cleanly.

---

## Session 02 — Commit 04: `config-and-security`
*2026-06-04*

**Approach:** Phase 1 reads — confirmed pyproject.toml has all required deps (pydantic-settings, python-jose[cryptography], passlib[bcrypt]), confirmed core/__init__.py exists as empty stub. Phase 2 writes — created config.py and security.py per spec.

**Files created:**
- `backend/app/core/config.py` — pydantic-settings Settings class with all env vars, settings singleton
- `backend/app/core/security.py` — hash_password, verify_password, create_access_token, decode_token

**Test gate results:**
- `from app.core.config import settings` import: PASS
- `from app.core.security import hash_password, verify_password` import: PASS
- `hash_password("test")` returns bcrypt hash: PASS
- `verify_password("test", hash_password("test"))` returns True: PASS
- `decode_token(create_access_token({"sub": "test"}))` returns `{"sub": "test"}`: PASS
- `decode_token("bad-token")` raises HTTPException 401: PASS

**Decisions made:**
- Replaced passlib CryptContext with direct `bcrypt` module calls. Passlib's bcrypt backend detection throws a ValueError on newer bcrypt versions (>= 4.x) due to the wrap-bug probe using a 73-byte test password. Direct `bcrypt.hashpw` / `bcrypt.checkpw` calls are stable and produce identical `$2b$` hashes. The `passlib[bcrypt]` dep remains in pyproject.toml as it was not removed — only the call site changed.

**Handoffs out:**
- → Rex (C08): `create_access_token` accepts `data: dict` — caller must pass `{"sub": str(user.id), "role": user.role}`
- → Rex (C09): `decode_token` raises HTTPException 401 — `get_current_user` dependency catches this naturally

---

## Session 03 — Commit 06: `sqlalchemy-models`
*2026-06-05*

**Approach:** Phase 1 reads — confirmed `database.py` exports `Base` (DeclarativeBase), confirmed `models/__init__.py` was empty (1 line), confirmed `pgvector>=0.2.0` in pyproject.toml. Phase 2 writes — created all 8 model files plus updated `__init__.py`.

**Files created:**
- `backend/app/models/user.py` — User model, CheckConstraint on role
- `backend/app/models/vendor.py` — Vendor model, all nullable fields
- `backend/app/models/shipment.py` — Shipment model, FK→vendors CASCADE
- `backend/app/models/category.py` — Category model, unique name
- `backend/app/models/product.py` — Product model, FK→shipments CASCADE, nullable FKs for category and added_by
- `backend/app/models/conversation.py` — Conversation model, two CheckConstraints
- `backend/app/models/message.py` — Message model, CheckConstraint on role, composite Index on (conversation_id, created_at)
- `backend/app/models/policy.py` — PolicyDocument + PolicyChunk models; PolicyChunk uses `Vector(1536)` from pgvector.sqlalchemy

**Files updated:**
- `backend/app/models/__init__.py` — imports all 9 model classes, full `__all__`

**Test gate results:**
- `from app.models import User, Vendor, Shipment, Category, Product, Conversation, Message, PolicyDocument, PolicyChunk`: PASS (with dummy env vars — `DATABASE_URL` and `SECRET_KEY` required at import time by pydantic-settings)

**Decisions made:**
- PolicyChunk IVFFlat index on `embedding` cannot be expressed as a standard SQLAlchemy `Index` without pgvector-specific DDL. Left `__table_args__` as an empty dict tuple — the index will be created in the Alembic migration (`op.execute("CREATE INDEX ...")`) at C07.
- `added_by` (Product) and `uploaded_by` (PolicyDocument) are nullable FKs with no CASCADE — intentional per spec.

**Handoffs out:**
- → Rex (C07): `models/__init__.py` imports all models — Alembic `env.py` will import `Base.metadata` from `app.core.database` and models from `app.models` to populate it
