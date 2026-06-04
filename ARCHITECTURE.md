# ARCHITECTURE.md — Manifesto

> Maintained by Claude. Every new component, data flow, or structural pattern introduced
> during this project is documented here as it is built.
> Last updated: 2026-06-04 (C01)

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

*This document is updated by Claude before every Team Lead approval prompt when a new component, pattern, or data flow is introduced.*
