# Manifesto — Cowork Handoff Prompt

Paste this entire prompt into Claude Cowork to scaffold the project.

---

## Your task

You are scaffolding a new full-stack web application called **Manifesto** from scratch. This is Phase 1 — core inventory management, no AI yet. Your job is to create the complete project structure, all configuration files, database models, and a working skeleton so development can begin immediately.

Do not build features. Do not write business logic beyond what is needed to make the skeleton run. The goal is: `docker-compose up` works, the API starts, the database migrates cleanly, and the frontend renders a login page.

---

## What this product is

Manifesto is an internal logistics and inventory management platform with an AI chat layer. It tracks vendors, shipments, and products, and lets managers query their inventory in plain English. Employees use it to ask policy questions via RAG chat.

The name comes from the cargo manifest — the document that records what a shipment contains, where it came from, and who sent it.

---

## Tech stack

**Backend**
- Python 3.12
- FastAPI (async)
- SQLAlchemy 2.0 (async, with `asyncpg`)
- Alembic (migrations)
- PostgreSQL 16 with `pgvector` extension
- JWT auth via `python-jose` + `passlib[bcrypt]`
- `pydantic-settings` for config
- `structlog` for logging

**Frontend**
- React 18 + Vite
- TypeScript
- Tailwind CSS
- Zustand (state)
- Axios + React Query (TanStack Query v5)
- React Router v6

**Infrastructure**
- Docker + docker-compose for local dev
- Ollama container (for local LLM — not wired up in Phase 1, just included in compose)

---

## Three user roles

| Role | Description |
|---|---|
| `admin` | All manager permissions + user management panel |
| `manager` | Inventory dashboard, vendors, shipments, products, both chat types |
| `employee` | Policy chat only |

Role is stored in the JWT payload and enforced via FastAPI dependencies.

---

## Database schema

Create all tables now, even those used in later phases. Alembic should generate a single initial migration from these models.

```sql
-- users
id UUID PK, name TEXT, email TEXT UNIQUE, password_hash TEXT,
role TEXT CHECK IN ('admin','manager','employee'), is_active BOOL DEFAULT TRUE,
created_at TIMESTAMPTZ

-- vendors
id UUID PK, name TEXT, contact TEXT, email TEXT, country TEXT, created_at TIMESTAMPTZ

-- shipments
id UUID PK, vendor_id UUID FK→vendors, arrived_at TIMESTAMPTZ, notes TEXT, created_at TIMESTAMPTZ

-- categories
id UUID PK, name TEXT UNIQUE

-- products
id UUID PK, shipment_id UUID FK→shipments, category_id UUID FK→categories,
name TEXT, description TEXT, quantity INT DEFAULT 0, unit TEXT,
added_by UUID FK→users, created_at TIMESTAMPTZ

-- conversations
id UUID PK, user_id UUID FK→users, chat_type TEXT CHECK IN ('policy','logistics'),
llm_provider TEXT CHECK IN ('ollama','openai'), title TEXT,
created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

-- messages
id UUID PK, conversation_id UUID FK→conversations, role TEXT CHECK IN ('user','assistant'),
content TEXT, sql_query TEXT, created_at TIMESTAMPTZ
INDEX ON (conversation_id, created_at)

-- policy_documents
id UUID PK, title TEXT, file_path TEXT, uploaded_by UUID FK→users, uploaded_at TIMESTAMPTZ

-- policy_chunks
id UUID PK, document_id UUID FK→policy_documents, chunk_index INT,
content TEXT, embedding VECTOR(1536), created_at TIMESTAMPTZ
INDEX USING ivfflat (embedding vector_cosine_ops)
```

---

## Project file structure to create

```
manifesto/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py          — POST /auth/login
│   │   │       ├── admin.py         — user CRUD (admin only)
│   │   │       ├── vendors.py       — vendor CRUD
│   │   │       ├── shipments.py     — shipment CRUD
│   │   │       ├── products.py      — product CRUD + search
│   │   │       ├── chat.py          — conversation + message endpoints (stub)
│   │   │       └── documents.py     — policy doc upload (stub)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py            — Settings via pydantic-settings
│   │   │   ├── security.py          — JWT + bcrypt helpers
│   │   │   └── database.py          — async engine + session factory
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── vendor.py
│   │   │   ├── shipment.py
│   │   │   ├── product.py
│   │   │   ├── category.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   └── policy.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── vendor.py
│   │   │   ├── shipment.py
│   │   │   ├── product.py
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm.py               — LLMService stub (Ollama + OpenAI interface)
│   │   │   ├── rag_policy.py        — stub
│   │   │   ├── rag_logistics.py     — stub
│   │   │   └── ingestion.py         — stub
│   │   └── dependencies.py          — get_current_user, require_role
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py      — generated from models
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── requirements.txt
│   └── seed.py                      — creates one admin user for local dev
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                  — router setup with role-based guards
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx        — placeholder, "Coming soon" is fine
│   │   │   ├── ChatPolicy.tsx       — placeholder
│   │   │   ├── ChatLogistics.tsx    — placeholder
│   │   │   └── Admin.tsx            — placeholder
│   │   ├── components/
│   │   │   └── ProtectedRoute.tsx   — role-based route guard
│   │   ├── store/
│   │   │   └── auth.ts              — Zustand auth slice (token, user, role)
│   │   └── api/
│   │       ├── client.ts            — Axios instance with JWT interceptor
│   │       └── auth.ts              — login API call
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── .env.example
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## docker-compose.yml services

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: manifesto
      POSTGRES_USER: manifesto
      POSTGRES_PASSWORD: manifesto
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db]
    env_file: .env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes: [./backend:/app]
```

---

## Key implementation details

**config.py** — use `pydantic-settings`. Required env vars:
```
DATABASE_URL=postgresql+asyncpg://manifesto:manifesto@db:5432/manifesto
SECRET_KEY=changeme
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OLLAMA_BASE_URL=http://ollama:11434
OPENAI_API_KEY=  # optional, empty in dev
```

**security.py** — implement:
- `hash_password(plain: str) -> str`
- `verify_password(plain: str, hashed: str) -> bool`
- `create_access_token(data: dict) -> str`
- `decode_token(token: str) -> dict`

**dependencies.py** — implement:
- `get_current_user` — FastAPI dependency, decodes JWT, fetches user from DB
- `require_role(*roles)` — returns a dependency that raises 403 if user role not in allowed roles

**auth.py route** — `POST /auth/login` accepts `{ email, password }`, returns `{ access_token, token_type: "bearer" }`.

**main.py** — include all routers, add CORS middleware (allow all origins in dev), add structlog middleware.

**seed.py** — creates a default admin user:
```
email: admin@manifesto.local
password: admin123
role: admin
```
Run with `python seed.py` after migrations.

**LLMService stub** (llm.py) — define the interface but raise `NotImplementedError` for now:
```python
class LLMService:
    def __init__(self, provider: Literal["ollama", "openai"]): ...
    async def chat(self, messages: list[dict]) -> AsyncIterator[str]: ...
    async def embed(self, text: str) -> list[float]: ...
```

**Frontend auth flow**:
- Login page POSTs to `/auth/login`, stores token in Zustand + localStorage
- Axios interceptor attaches `Authorization: Bearer <token>` to all requests
- `ProtectedRoute` component checks role from Zustand store and redirects if unauthorized
- On 401 response, clear token and redirect to `/login`

---

## Definition of done for Phase 1 scaffold

- [ ] `docker-compose up` starts without errors
- [ ] `GET /docs` shows FastAPI OpenAPI UI with all routes listed
- [ ] `POST /auth/login` with seed credentials returns a valid JWT
- [ ] `GET /api/v1/vendors` with a valid manager token returns `[]`
- [ ] `GET /api/v1/vendors` without a token returns `401`
- [ ] `GET /api/v1/admin/users` with a manager token returns `403`
- [ ] `GET /api/v1/admin/users` with the admin token returns the seed user
- [ ] Alembic migration runs cleanly: `alembic upgrade head`
- [ ] Frontend `npm run dev` renders the login page without errors
- [ ] Login with seed credentials redirects to the dashboard placeholder

---

## What NOT to do

- Do not implement RAG, embeddings, or LLM calls — those are Phase 2 and 3
- Do not build the full dashboard UI — a placeholder with the page title is enough
- Do not add tests — that comes after the skeleton is confirmed working
- Do not add pagination, filtering, or search to list endpoints — keep them simple for now
- Do not use `sync` SQLAlchemy — everything must be `async`

---

## Reference files

The full project specification is in `manifesto-spec.md`. The pitch deck is `manifesto-pitch.pptx`. Both are in the project folder alongside this prompt.
