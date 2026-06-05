# ARCHITECTURE.md — Manifesto

> Maintained by Claude. Every new component, data flow, or structural pattern introduced
> during this project is documented here as it is built.
> Last updated: 2026-06-04 (C02)

---

## Overview

Manifesto is a logistics RAG platform with a FastAPI backend, PostgreSQL + pgvector database,
a local LLM layer via Ollama, and a React + Vite frontend. All services run in Docker Compose
for local development.

---

## C01 — Project Scaffold

**Introduced by:** Adam (DevOps), Commit 01

### Container Stack (docker-compose.yml)

```
┌─────────────────────────────────────────────────────────┐
│ docker-compose                                          │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │    db    │    │  ollama  │    │     backend      │  │
│  │ pg16 +   │    │  :11434  │    │  FastAPI :8000   │  │
│  │ pgvector │    │          │    │  depends_on: db  │  │
│  │  :5432   │    │          │    │  (service_healthy)│  │
│  └──────────┘    └──────────┘    └──────────────────┘  │
│       │                                   │             │
│  postgres_data                      ./backend:/app      │
│  (named vol)        ollama_data     (bind mount, dev)   │
└─────────────────────────────────────────────────────────┘
```

**Services:**

| Service | Image | Port | Volume | Notes |
|---|---|---|---|---|
| db | pgvector/pgvector:pg16 | 5432 | postgres_data (named) | healthcheck: pg_isready |
| ollama | ollama/ollama | 11434 | ollama_data (named) | local LLM serving |
| backend | ./backend (build) | 8000 | ./backend:/app (bind) | depends_on db healthy |

**Startup dependency:** `backend` waits for `db` healthcheck to pass before starting.

### Backend Dockerfile

```
python:3.12-slim
  └── pip install uv
       └── COPY pyproject.toml
            └── uv sync
                 └── CMD uvicorn app.main:app --reload
```

`pyproject.toml` is Rex's responsibility (C02). Dockerfile build will fail until C02 lands — expected.

### Environment Variables (.env.example)

| Variable | Purpose | Owner |
|---|---|---|
| DATABASE_URL | asyncpg connection string | Rex (reads), Adam (defines format) |
| SECRET_KEY | JWT signing key | Rex |
| ALGORITHM | JWT algorithm | Rex |
| ACCESS_TOKEN_EXPIRE_MINUTES | JWT access TTL | Rex |
| REFRESH_TOKEN_EXPIRE_DAYS | JWT refresh TTL | Rex |
| OLLAMA_BASE_URL | Local LLM endpoint | Rex/Nova |
| OPENAI_API_KEY | Cloud LLM fallback | Rex/Nova |

### Directory Structure (after C01)

```
manifesto/
├── backend/
│   └── Dockerfile
├── hooks/
│   └── pre_commit_check.py  (+ sh wrapper at .git/hooks/pre-commit)
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

`backend/app/` and `frontend/` do not yet exist — Rex creates `backend/app/` in C02, Aria creates `frontend/` in C03.

---

## C02 — Python Skeleton

**Introduced by:** Rex (Backend), Commit 02

### Backend Application Structure

```
backend/
├── pyproject.toml          ← project metadata + all dependencies (uv managed)
├── app/
│   ├── __init__.py
│   ├── main.py             ← FastAPI app entry point
│   ├── dependencies.py     ← empty stub (auth deps added C09)
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
```

### FastAPI App Bootstrap (main.py)

- `FastAPI(title="Manifesto", version="0.1.0")` with CORS middleware (allow all origins — tighten in production)
- `structlog` logger at module level
- `GET /` returns `{"status": "ok"}` — health check only
- `# routers registered below` comment block — all future route commits append here

### Dependency Stack (pyproject.toml)

| Package | Purpose |
|---|---|
| fastapi, uvicorn[standard] | Web framework + ASGI server |
| sqlalchemy[asyncio], asyncpg | Async ORM + PostgreSQL driver |
| alembic | Database migrations |
| pydantic-settings | Config from environment |
| python-jose[cryptography], passlib[bcrypt] | JWT auth |
| pgvector | Vector similarity search |
| pymupdf, python-docx | Document parsing (PDF, Word) |
| structlog | Structured logging |
| python-multipart | File upload support |

### uv Environment

`uv sync` creates `.venv/` inside `backend/` and installs all deps. Lock file: `uv.lock`. All agents working in `backend/` must use `uv add <package>` — never `pip install`.

---

## C03 — Frontend Scaffold

**Introduced by:** Aria (Frontend), Commit 03

### Frontend Application Structure

```
frontend/
├── package.json            ← React 18, Vite, TypeScript, Tailwind, Zustand, Axios, TanStack Query, React Router
├── package-lock.json       ← npm lockfile
├── vite.config.ts          ← Vite config; proxy /api + /auth → http://localhost:8000
├── tailwind.config.ts      ← Tailwind content paths: src/**/*.{ts,tsx}
├── tsconfig.json           ← TypeScript strict mode; moduleResolution: bundler; noEmit: true
├── postcss.config.js       ← PostCSS config (required by Tailwind v3 for Vite CSS processing)
├── index.html              ← HTML entry point; <div id="root">; loads src/main.tsx
├── .env.example            ← VITE_API_BASE_URL=http://localhost:8000
└── src/
    ├── main.tsx            ← ReactDOM.createRoot renders App into #root (StrictMode)
    ├── App.tsx             ← Stub: returns <div>Manifesto</div>; routing added C18
    └── index.css           ← Tailwind directives: @tailwind base/components/utilities
```

### Vite Proxy

```
/api  → http://localhost:8000
/auth → http://localhost:8000
```

All API and auth requests from the frontend are proxied to the FastAPI backend at port 8000 during development.

### TypeScript Config Notes

- `"moduleResolution": "bundler"` + `"allowImportingTsExtensions": true` — standard Vite + TypeScript strict setup
- `"noEmit": true` — TypeScript only type-checks; Vite handles transpilation
- Strict flags on: `strict`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`

### Frontend Dependency Stack

| Package | Purpose |
|---|---|
| react 18 + react-dom | UI framework |
| @vitejs/plugin-react | Vite React plugin (JSX transform) |
| typescript 5 | Type safety; strict mode |
| tailwindcss 3 + postcss + autoprefixer | Utility-first CSS |
| react-router-dom 6 | Client-side routing (wired in C18) |
| zustand 4 | In-memory state management (auth store added C17) |
| axios 1 | HTTP client (instance + interceptors added C17) |
| @tanstack/react-query 5 | Server state caching (configured C17) |

---

## C04 — Config and Security

**Introduced by:** Rex (Backend), Commit 04

### Application Configuration (config.py)

`Settings` class inherits `pydantic_settings.BaseSettings`. Reads from `.env` file + environment.

| Field | Default | Purpose |
|---|---|---|
| DATABASE_URL | (required) | asyncpg connection string |
| SECRET_KEY | (required) | JWT signing key |
| ALGORITHM | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | JWT access TTL |
| REFRESH_TOKEN_EXPIRE_DAYS | 7 | JWT refresh TTL |
| OLLAMA_BASE_URL | http://ollama:11434 | Local LLM endpoint |
| OPENAI_API_KEY | "" | Cloud LLM fallback (optional) |

Settings singleton: `from app.core.config import settings`.

### Security Utilities (security.py)

| Function | Signature | Notes |
|---|---|---|
| `hash_password` | `(plain: str) → str` | bcrypt hash via direct `bcrypt` library |
| `verify_password` | `(plain: str, hashed: str) → bool` | bcrypt verify |
| `create_access_token` | `(data: dict) → str` | JWT with expiry delta; claims: `{"sub": ..., "exp": ...}` |
| `decode_token` | `(token: str) → dict` | Decodes JWT; raises HTTP 401 on any `InvalidTokenError` |

**Library changes from C02 spec:**
- `passlib` removed → `bcrypt` used directly (version incompatibility)
- `python-jose` removed → `PyJWT>=2.8.0` (see D16)

---

## C04b — Config Security Hardening

**Introduced by:** Rex (Backend), Commit 04b — Sage gate deferred findings from C04 (see D15)

No new files. No interface changes.

| File | Change |
|---|---|
| `config.py` | `field_validator` on `SECRET_KEY` — rejects values shorter than 32 chars; fails fast at startup |
| `security.py` | `structlog.get_logger()` + `logger.warning("token_validation_failed", error=str(exc))` in `decode_token` catch block — structured forensics; external error message unchanged |

---

## C05 — Database Session

**Introduced by:** Claude (direct write — spec fully prescriptive), Commit 05

### Async Database Layer (database.py)

```
app.core.database
├── engine              ← AsyncEngine (create_async_engine, echo=False)
├── AsyncSessionLocal   ← async_sessionmaker(engine, expire_on_commit=False)
├── Base                ← DeclarativeBase — all models inherit from this
└── get_db()            ← FastAPI async generator dependency → yields AsyncSession
```

**Downstream contracts:**
- C06 (models): all ORM models must do `class MyModel(Base)`
- C07 (Alembic): `env.py` imports `engine` and `Base.metadata` for async migrations

**Viktor batch wave verdict (C01–C05): PASS** — no findings.

---

## C06 — SQLAlchemy Models

**Introduced by:** Rex (Backend), Commit 06

### ORM Model Layer

All 9 models defined in `backend/app/models/`. All inherit from `Base` (C05). All UUIDs are Postgres-generated via `server_default=text("gen_random_uuid()")`.

| Model | Table | Key relationships |
|---|---|---|
| `User` | `users` | Referenced by Product (added_by), Conversation (user_id), PolicyDocument (uploaded_by) |
| `Vendor` | `vendors` | Parent of Shipment |
| `Shipment` | `shipments` | FK→vendors CASCADE; parent of Product |
| `Category` | `categories` | Referenced by Product (nullable FK) |
| `Product` | `products` | FK→shipments CASCADE; FK→categories nullable; FK→users (added_by) nullable |
| `Conversation` | `conversations` | FK→users CASCADE; parent of Message |
| `Message` | `messages` | FK→conversations CASCADE; composite index on (conversation_id, created_at) |
| `PolicyDocument` | `policy_documents` | FK→users (uploaded_by) nullable; parent of PolicyChunk |
| `PolicyChunk` | `policy_chunks` | FK→policy_documents CASCADE; `Vector(1536)` embedding (pgvector) |

### Constraints

All finite-value string fields use `CheckConstraint` for DB-level enforcement:
- `User.role`: `IN ('admin', 'manager', 'employee')`
- `Conversation.chat_type`: `IN ('policy', 'logistics')`
- `Conversation.llm_provider`: `IN ('ollama', 'openai')`
- `Message.role`: `IN ('user', 'assistant')`

### IVFFlat index

`PolicyChunk.embedding` requires pgvector-specific DDL (`USING ivfflat (embedding vector_cosine_ops)`). Not expressible as a standard SQLAlchemy `Index`. Deferred to C07 Alembic migration via `op.execute(...)`. See D17.

### Alembic discovery

`backend/app/models/__init__.py` imports all 9 model classes. Alembic's `env.py` (C07) imports this module — the side-effect populates `Base.metadata` with all table definitions.

---

## C07 — Alembic Migration

**Introduced by:** Rex (Backend), Commit 07

### Migration Infrastructure

```
backend/
├── alembic.ini                         ← Alembic config; sqlalchemy.url overridden at runtime by DATABASE_URL env var
└── alembic/
    ├── env.py                          ← async runner: imports Base + engine from app.core.database; uses connection.run_sync
    ├── script.py.mako                  ← standard migration template
    └── versions/
        └── 0001_initial.py             ← initial schema: all 9 tables + indexes + CHECK constraints
```

### env.py Pattern

Imports `Base` and `engine` directly from `app.core.database` (not `async_engine_from_config`). All model imports happen via `from app.models import *` which populates `Base.metadata` as a side effect. Migration runs inside an async context using `connection.run_sync(do_run_migrations)`.

### Initial Migration (0001_initial)

Order of operations:
1. `CREATE EXTENSION IF NOT EXISTS vector` — pgvector
2. `CREATE EXTENSION IF NOT EXISTS pgcrypto` — supports `gen_random_uuid()` server defaults
3. Tables in FK dependency order: `users → vendors → categories → shipments → products → conversations → messages → policy_documents → policy_chunks`
4. `ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector(1536)` — pgvector DDL requires ALTER after table creation
5. `CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)` — D17 deferred index

### Operational Constraint

All Alembic (and any other asyncpg) commands must run inside the Docker container — not from the Windows host. A native Windows Postgres instance occupies `localhost:5432` and intercepts connections before Docker's port mapping. Run as:
```
docker-compose run --rm --no-deps backend sh -c "cd /app && uv run alembic upgrade head"
```
See D18.

---

## C09 — Auth Dependencies

**Introduced by:** Rex (Backend), Commit 09

### FastAPI Auth Dependency Layer (dependencies.py)

```
app.dependencies
├── oauth2_scheme          ← OAuth2PasswordBearer(tokenUrl="/auth/login")
├── get_current_user()     ← async dependency: validates JWT → fetches User from DB → checks is_active
└── require_role(*roles)   ← factory → returns async _check_role dependency → raises 403 if role not in roles
```

### get_current_user flow

```
Request header: Authorization: Bearer <token>
        │
        ▼
oauth2_scheme extracts token string
        │
        ▼
decode_token(token)   ── invalid/expired ──► HTTP 401
        │
        ▼
payload["sub"] = user_id
        │
        ▼
DB: SELECT * FROM users WHERE id = user_id
        │
   not found / inactive ──► HTTP 401
        │
        ▼
return User ORM object
```

### require_role pattern

```python
require_role("admin")          # use as: Depends(require_role("admin"))
require_role("admin", "manager")  # passes if user.role is either
```

Returns a new async dependency each call. The inner `_check_role` calls `get_current_user` (full auth chain) then enforces the role constraint.

### Accepted trade-off (D19)

User state (`is_active`, `role`) is fetched once per request from the DB. JWT tokens are not revoked on user deactivation — a deactivated user's token remains valid for up to `ACCESS_TOKEN_EXPIRE_MINUTES`. If immediate revocation is needed in a future phase, add a token denylist.

### Downstream contracts

- All protected routes use `Depends(get_current_user)` or `Depends(require_role(...))`
- C10 (login route): issues tokens with `{"sub": str(user.id), "role": user.role}` — `sub` is always the authenticated user's own ID
- C11 (admin routes): `Depends(require_role("admin"))`
- C12–C14 (inventory routes): `Depends(require_role("admin", "manager"))`

---

---

## C10 — Auth Route

**Introduced by:** Claude (direct write — spec fully prescriptive), Commit 10

### Login Endpoint

`POST /auth/login` registered via `app.include_router(auth_router, prefix="/auth", tags=["auth"])`.

#### New files

| File | Purpose |
|---|---|
| `backend/app/schemas/auth.py` | `LoginRequest` (email, password) + `TokenResponse` (access_token, token_type="bearer") |
| `backend/app/api/v1/auth.py` | `POST /auth/login` route handler |

#### Login flow

```
POST /auth/login {email, password}
        │
        ▼
SELECT * FROM users WHERE email = request.email
        │
  not found / inactive ──► HTTP 401 "Invalid credentials"
        │
        ▼
verify_password(request.password, user.password_hash)
        │
  fails ──────────────────► HTTP 401 "Invalid credentials"
        │
        ▼
create_access_token({"sub": str(user.id), "role": user.role})
        │
        ▼
{"access_token": "...", "token_type": "bearer"}
```

Error messages are identical for all failure cases — no field-level disclosure.

#### Infrastructure fix (D14 follow-on)

`docker-compose.yml` backend command corrected from `uvicorn ...` to `uv run uvicorn ...`. The volume mount `./backend:/app` replaces the container `/app` with local Windows `.venv/`, hiding Linux uvicorn binaries. `uv run` handles binary resolution regardless of platform.

#### Downstream contracts

- Aria (C17): Token format is `{access_token: string, token_type: "bearer"}`. Store `access_token` in Zustand, attach as `Authorization: Bearer <token>` header.
- C11–C14: protected routes use `Depends(require_role(...))` per C09.

#### Gate wave verdict (C10 — commit #10 + auth trigger)

| Reviewer | Finding | Verdict |
|---|---|---|
| Viktor | BLOCK: timing on inactive-user check | Dismissed — superseded by Sage WARN (D20) |
| Viktor | WARN: no EmailStr/Field validation | Noted — future hardening |
| Sage | WARN: timing side-channel (email enumeration) | Accepted trade-off (D20) |
| Sage | WARN: no max_length on LoginRequest fields | Noted — future hardening |
| Sage | C09 Finding #1 re-evaluation | CLOSED — token issued only after verify_password passes |

---

## C11 — Admin Routes

**Introduced by:** Rex (Backend), Commit 11

### User Management API

```
backend/app/
├── api/v1/admin.py     ← admin router (GET/POST/PUT user management)
└── schemas/user.py     ← UserRead, UserCreate, UserUpdate schemas
```

`main.py` updated: `app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])`

### Routes

| Method | Path | Auth | Response | Notes |
|---|---|---|---|---|
| GET | `/api/v1/admin/users` | `require_role("admin")` | `list[UserRead]` | Returns all users, no pagination |
| POST | `/api/v1/admin/users` | `require_role("admin")` | `UserRead` (201) | 409 on duplicate email |
| PUT | `/api/v1/admin/users/{user_id}` | `require_role("admin")` | `UserRead` | 404 if not found; skips None fields |

### Schemas (backend/app/schemas/user.py)

```python
UserRead    — id, name, email, role, is_active, created_at  (model_config from_attributes=True)
UserCreate  — name, email, password, role: Literal["admin","manager","employee"]
UserUpdate  — role: Literal[...] | None, is_active: bool | None
```

### Patterns established for C12–C14

- `Depends(require_role("admin"))` pattern for all admin-only routes
- `model_config = {"from_attributes": True}` on all response schemas that wrap ORM objects
- Path params for UUID columns typed as `str`, not `uuid.UUID` — see D21
- Duplicate-check guard on POST before insert (409 > opaque DB IntegrityError to client)

### Downstream contracts

- Aria (C19): `GET /api/v1/admin/users` returns `UserRead` list — fields: id, name, email, role, is_active, created_at. Requires `Authorization: Bearer <admin-token>`.

---

*This document is updated by Claude before every Team Lead approval prompt when a new component, pattern, or data flow is introduced.*
