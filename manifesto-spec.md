# Manifesto — Project Specification

> **Status**: Pre-development
> **Authors**: Brainstorm session — Eran Mani, Andrej Karpathy, Boris Cherny
> **Date**: June 2026
> **Tagline**: *Your inventory, your policies — instantly searchable.*

---

## 1. Project Overview

**Manifesto** is an internal web application for managing vendor logistics and inventory, with an integrated AI chat layer serving two distinct audiences.

The name comes from the cargo manifest — the shipping document that records what a delivery contains, where it came from, and who sent it. That's the core of what this product does: it gives every person in an organisation a single, searchable record of everything that has ever arrived, and the intelligence to query it in plain language.

| Audience | What they get |
|---|---|
| Managers | Full inventory visibility, vendor tracking, shipment history, natural language queries over live data |
| Employees | Policy Q&A via RAG chat — cited answers from uploaded company documents, no manager required |
| Senior / Admin managers | User management panel for creating manager and employee accounts |

The application is split into two major functional areas:

| Area | Description |
|---|---|
| **Inventory management** | Browse, search, and input products; view vendor details and shipment history |
| **AI chat** | Two separate pipelines — policy Q&A for employees, logistics Q&A for managers |

---

## 2. Goals and Non-Goals

### Goals
- Give managers a clear, searchable view of all inventory items with full provenance (vendor, shipment, arrival date, contents)
- Allow managers to add new products through a structured input form
- Allow employees to get answers to policy questions without escalating to a manager, with document citations
- Allow managers to query inventory using natural language ("What arrived from Vendor X last month?")
- Persist conversation history per user so the chat feels personal and continuous across sessions
- Support both local (Ollama) and cloud (OpenAI) LLM providers, selectable per session

### Non-Goals (for now)
- No real-time external integrations (no supplier APIs, no ERP sync)
- No mobile-native app — web only
- No automated re-ordering or stock alerts (future phase)
- No multi-tenant / multi-company support

---

## 3. User Roles

Manifesto has three roles, managed by a senior manager via the admin UI.

| Role | Access |
|---|---|
| `admin` | All manager permissions + user management (create, deactivate accounts) |
| `manager` | Inventory dashboard, add product, vendor pages, logistics chat, policy chat |
| `employee` | Policy chat only |

Role is stored in the JWT payload and enforced on every API route via FastAPI dependencies. The admin UI is a protected route accessible only to users with the `admin` role.

---

## 4. Database Design

### Why PostgreSQL

NoSQL was considered and rejected. The data model is inherently relational:
- A vendor has many shipments
- A shipment has many products
- Products belong to a category
- A user has many conversations, each with many messages

NoSQL would require duplicating vendor data across every product document or solving joins in application code. PostgreSQL handles this natively, and with the `pgvector` extension it also handles the embedding store for RAG — one database for everything.

### Schema (v1)

```sql
-- Users
CREATE TABLE users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    email        TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role         TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'employee')),
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Vendors
CREATE TABLE vendors (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    contact     TEXT,
    email       TEXT,
    country     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Shipments (a delivery event from a vendor)
CREATE TABLE shipments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id     UUID REFERENCES vendors(id) ON DELETE CASCADE,
    arrived_at    TIMESTAMPTZ NOT NULL,
    notes         TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Product categories
CREATE TABLE categories (
    id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name  TEXT UNIQUE NOT NULL
);

-- Products (individual items in a shipment)
CREATE TABLE products (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id   UUID REFERENCES shipments(id) ON DELETE CASCADE,
    category_id   UUID REFERENCES categories(id),
    name          TEXT NOT NULL,
    description   TEXT,
    quantity      INT NOT NULL DEFAULT 0,
    unit          TEXT,            -- e.g. "kg", "units", "pcs"
    added_by      UUID REFERENCES users(id),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Chat conversations (persisted per user)
CREATE TABLE conversations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    chat_type    TEXT NOT NULL CHECK (chat_type IN ('policy', 'logistics')),
    llm_provider TEXT NOT NULL CHECK (llm_provider IN ('ollama', 'openai')),
    title        TEXT,            -- auto-generated from first message
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Chat messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    sql_query       TEXT,         -- populated for logistics chat responses
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON messages (conversation_id, created_at);

-- Policy documents (for RAG ingestion)
CREATE TABLE policy_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    file_path   TEXT,
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Policy chunks with embeddings (pgvector)
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

### Key Relationships

```
users (1) ──── (N) conversations (1) ──── (N) messages

vendors (1) ──── (N) shipments (1) ──── (N) products
                                               │
                                    categories (1) ──── (N) products

policy_documents (1) ──── (N) policy_chunks
```

---

## 5. LLM Provider Abstraction

One of Manifesto's differentiators is that it is LLM-agnostic. Users select a provider when starting a new conversation. The choice is stored on the `conversations` record and used for the lifetime of that conversation.

### Supported providers

| Provider | Model | Use case |
|---|---|---|
| `ollama` | `llama3` (or any local model) | Local dev, testing, privacy-sensitive deployments |
| `openai` | `gpt-4o` + `text-embedding-3-small` | Production, higher quality answers |

### Abstraction layer

A single `LLMService` class in `app/services/llm.py` wraps both providers behind a common interface:

```python
class LLMService:
    def __init__(self, provider: Literal["ollama", "openai"]):
        self.provider = provider

    async def chat(self, messages: list[dict], stream: bool = True) -> AsyncIterator[str]:
        if self.provider == "openai":
            return self._openai_chat(messages, stream)
        return self._ollama_chat(messages, stream)

    async def embed(self, text: str) -> list[float]:
        if self.provider == "openai":
            return self._openai_embed(text)
        return self._ollama_embed(text)
```

This means all RAG pipelines call `LLMService` — swapping providers requires no changes to business logic.

### Embedding dimension note

Ollama embeddings (e.g. `nomic-embed-text`) use 768 dimensions. OpenAI `text-embedding-3-small` uses 1536. The `policy_chunks.embedding` column must match the provider used at ingestion time. For MVP, pick one provider for ingestion and stay consistent. A future migration path: store which provider embedded each chunk and filter at query time.

---

## 6. Backend Architecture

### Technology Stack

| Component | Choice | Rationale |
|---|---|---|
| Framework | FastAPI | Async-native, Pydantic schemas, OpenAPI docs out of the box |
| ORM | SQLAlchemy 2 (async) | Mature, Alembic migrations, works with asyncpg |
| Migrations | Alembic | Standard pairing with SQLAlchemy |
| Database | PostgreSQL 16 + pgvector | Relational + vector search in one DB |
| LLM (cloud) | OpenAI API (`gpt-4o`) | Production quality |
| LLM (local) | Ollama | Zero-cost local dev and on-premise deployments |
| Auth | JWT (python-jose) | Simple stateless auth |
| Containerisation | Docker + docker-compose | Local dev and production parity |

### API routes

```
FastAPI App
├── /auth
│   └── POST /login              — returns access + refresh tokens
├── /api/v1/admin
│   ├── GET  /users              — list all users (admin only)
│   ├── POST /users              — create user (admin only)
│   └── PUT  /users/{id}        — update role / deactivate (admin only)
├── /api/v1/vendors              — vendor CRUD
├── /api/v1/shipments            — shipment CRUD
├── /api/v1/products             — product CRUD + search
├── /api/v1/chat
│   ├── POST /conversations      — create conversation (sets provider + type)
│   ├── GET  /conversations      — list user's conversations
│   ├── GET  /conversations/{id}/messages
│   └── POST /conversations/{id}/messages  — send message, stream response
└── /api/v1/documents            — upload + ingest policy documents
```

### RAG Pipeline — Policy Chat (Employees)

Answers questions about company rules and procedures. Data source: uploaded policy documents.

```
Ingest (offline)
  Manager uploads PDF/DOCX/TXT →
  Backend extracts text (PyMuPDF / python-docx) →
  Split into chunks (512 tokens, 50 token overlap) →
  Embed each chunk via LLMService.embed() →
  Store chunks + embeddings in policy_chunks

Query (online, streaming)
  User sends message →
  Embed query via LLMService.embed() →
  Cosine similarity search in pgvector (top-k=5) →
  Build prompt with retrieved chunks + conversation history (last 6 messages) →
  Stream response via LLMService.chat() →
  Persist user message + assistant response to messages table
  Note document titles as citations in response metadata
```

**System prompt for policy chat:**
```
You are Manifesto, a company assistant. Answer only using the policy excerpts
provided below. If the answer is not found in the excerpts, say so clearly —
do not invent policies or procedures. Where relevant, cite which document your
answer comes from by name.
```

### RAG Pipeline — Logistics Chat (Managers)

Answers questions about live inventory data. Data source: the PostgreSQL database itself.

```
User sends message →
  Build text-to-SQL prompt (includes full schema + conversation history) →
  LLM generates a SELECT query →
  Execute on read-only DB connection (parameterised, no DDL/DML) →
  Format result rows as context →
  LLM synthesises natural language answer →
  Stream response to client →
  Persist user message + assistant response + sql_query to messages table
```

**Security note**: The logistics chat uses a dedicated read-only PostgreSQL role. The generated SQL is validated to be a `SELECT` statement before execution. No `INSERT`, `UPDATE`, `DELETE`, or DDL is ever executed from a chat prompt.

**Conversation history in logistics chat**: The last 6 messages are included in the prompt so managers can ask follow-up questions ("and how many of those arrived in Q1?") without re-stating context.

---

## 7. Frontend Architecture

### Technology Stack

| Component | Choice |
|---|---|
| Framework | React + Vite |
| Styling | Tailwind CSS |
| State | Zustand |
| HTTP | Axios + React Query |
| Chat UI | Custom streaming component (SSE) |

### Pages and Views

**Login**
- Email + password form
- On success: redirect to role-appropriate landing page

**Manager Dashboard**
- Inventory table: Product name, Category, Quantity, Vendor, Arrived at
- Filters: vendor, category, date range
- Full-text search on product name / description
- "Add Product" button → modal form

**Add Product Form**
- Fields: Name, Description, Quantity, Unit, Category (dropdown), Vendor (dropdown + inline create), Arrival date, Notes
- `POST /api/v1/products`

**Vendor Detail Page**
- Vendor info (name, contact, country)
- Chronological shipment timeline with expandable product lists per shipment

**Chat — Policy (employees + managers)**
- Conversation list in left sidebar (persistent history)
- "New conversation" button — prompts provider selection (Ollama / OpenAI)
- Streaming message UI
- Citations shown below assistant responses: "Source: Employee Handbook v3"
- Employees see only this chat; managers see both

**Chat — Logistics (managers only)**
- Same layout as policy chat
- SQL query shown as a collapsible block beneath each assistant answer (transparency)
- "New conversation" button with provider selection

**Admin Panel (admin role only)**
- User table: name, email, role, status (active / inactive)
- "Add user" form: name, email, temporary password, role
- Toggle to deactivate / reactivate accounts

### Role-based routing

| Route | Admin | Manager | Employee |
|---|---|---|---|
| `/dashboard` | ✓ | ✓ | — |
| `/vendors` | ✓ | ✓ | — |
| `/chat/logistics` | ✓ | ✓ | — |
| `/chat/policy` | ✓ | ✓ | ✓ |
| `/admin` | ✓ | — | — |

---

## 8. Authentication

JWT-based auth:

- `POST /auth/login` → `{ access_token, refresh_token }`
- Access token: 30 min expiry, contains `user_id` and `role`
- Refresh token: 7 day expiry, stored in `httpOnly` cookie
- FastAPI dependency `get_current_user` decodes and validates on every protected route
- Role checks via `require_role("admin")` dependency on admin routes
- Passwords hashed with `bcrypt`

No OAuth / SSO for now. Can be added in a later phase.

---

## 9. Chat History Persistence

Conversations are persisted per user. This means:

- Each user has a sidebar showing all their past conversations, grouped by type (policy / logistics)
- Conversation titles are auto-generated from the first user message (trimmed to 60 chars)
- Clicking a past conversation loads the full message history from the database
- The last 6 messages of a conversation are included as context in every new prompt
- Conversation records store which `llm_provider` was used — this is fixed at conversation creation and cannot be changed mid-conversation

**Schema recap:**
```
conversations: id, user_id, chat_type, llm_provider, title, created_at, updated_at
messages:      id, conversation_id, role, content, sql_query, created_at
```

---

## 10. Document Ingestion

Policy documents are uploaded by managers (any manager, not just admin) and indexed for the employee policy chat.

```
Manager uploads file via /api/v1/documents →
  Validate file type (PDF, DOCX, TXT, MD) →
  Extract text:
    PDF  → PyMuPDF
    DOCX → python-docx
    TXT/MD → read directly →
  Chunk with RecursiveCharacterTextSplitter (512 tokens, 50 overlap) →
  Embed each chunk via LLMService.embed() →
  Insert into policy_chunks with document_id + chunk_index →
  Return { document_id, title, chunk_count } confirmation
```

Employees do not see the list of policy documents. They only receive answers (with source citations embedded in the response). This is intentional — the document library is a management concern, not an employee-facing feature.

---

## 11. Project File Structure

```
manifesto/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── admin.py         — user management (admin only)
│   │   │       ├── auth.py          — login, token refresh
│   │   │       ├── vendors.py
│   │   │       ├── shipments.py
│   │   │       ├── products.py
│   │   │       ├── chat.py          — conversation + message endpoints
│   │   │       └── documents.py     — policy doc upload + ingest
│   │   ├── core/
│   │   │   ├── config.py            — pydantic-settings, env vars
│   │   │   ├── security.py          — JWT encode/decode, bcrypt
│   │   │   └── database.py          — async engine, session factory
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── vendor.py
│   │   │   ├── shipment.py
│   │   │   ├── product.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   └── policy.py
│   │   ├── schemas/                 — Pydantic request/response models
│   │   ├── services/
│   │   │   ├── llm.py               — LLMService (Ollama + OpenAI abstraction)
│   │   │   ├── rag_policy.py        — embed, retrieve, generate for policy chat
│   │   │   ├── rag_logistics.py     — text-to-SQL pipeline
│   │   │   └── ingestion.py         — document chunking + embedding
│   │   └── main.py
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── AddProduct.tsx
│   │   │   ├── VendorDetail.tsx
│   │   │   ├── ChatPolicy.tsx
│   │   │   ├── ChatLogistics.tsx
│   │   │   └── Admin.tsx
│   │   ├── components/
│   │   │   ├── ChatSidebar.tsx      — conversation list + new chat button
│   │   │   ├── MessageStream.tsx    — streaming SSE message renderer
│   │   │   ├── SqlBlock.tsx         — collapsible SQL display
│   │   │   └── ProviderSelect.tsx   — Ollama / OpenAI picker modal
│   │   ├── store/                   — Zustand slices
│   │   └── api/                     — typed Axios wrappers
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## 12. Development Phases

### Phase 1 — Core inventory (no AI)
- PostgreSQL schema + Alembic migrations (all tables including users, conversations, messages)
- Vendor, shipment, product CRUD APIs
- JWT auth with all three roles
- Admin panel for user management
- Manager dashboard + add-product form
- Vendor detail page

### Phase 2 — Policy RAG
- Document upload + ingestion pipeline
- pgvector setup and chunk embedding
- LLMService abstraction (Ollama + OpenAI)
- Employee + manager policy chat with streaming
- Conversation history persistence (sidebar + message reload)
- Citations in policy responses

### Phase 3 — Logistics RAG
- Text-to-SQL service
- Manager logistics chat with SQL transparency block
- Read-only DB connection for safety
- Conversation history in logistics context window

### Phase 4 — Hardening
- Input validation and error handling throughout
- Rate limiting on chat endpoints
- Prompt injection mitigations
- Logging and observability (structlog + request IDs)
- Docker compose for full local dev stack
- AWS deployment (S3 for file store, ECS or EC2 for app, RDS for PostgreSQL)

---

## 13. Deployment (Phase 4 target)

| Service | AWS resource |
|---|---|
| Backend (FastAPI) | ECS Fargate or EC2 |
| Frontend (React) | S3 + CloudFront |
| Database | RDS PostgreSQL 16 (pgvector extension) |
| File store (policy docs) | S3 bucket (private, signed URLs) |
| Domain | Route 53 + ACM certificate |

Local dev: full stack runs via `docker-compose up` — PostgreSQL, Ollama, and the FastAPI backend all in containers. Frontend runs via `vite dev` pointing at `localhost:8000`.

---

## 14. Resolved Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Who manages users? | Admin-role users have a dedicated `/admin` panel to create and deactivate manager/employee accounts |
| 2 | Chat history persistence | Persisted per user in `conversations` + `messages` tables. Sidebar shows history. Last 6 messages used as context window. |
| 3 | Policy document access for employees | Employees get answers and citations (document name) only. They do not see the document list. |
| 4 | LLM provider | Ollama for local dev + on-premise option. OpenAI for production. Provider selected at conversation creation via `LLMService` abstraction. |
| 5 | Deployment target | AWS — S3 + CloudFront (frontend), ECS/EC2 (backend), RDS (database). |

---

*This document is the working spec for all development phases. Update it as new decisions are made.*
