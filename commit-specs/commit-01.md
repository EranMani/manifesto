# Commit 01 — `project-scaffold` · Adam

**Phase:** 1A — Infrastructure Foundation
**Assignee:** Adam (DevOps)
**Depends on:** nothing — this is the first commit

---

## What

Create the full project directory structure, Docker infrastructure, and environment configuration.
No application code. No Python logic. No React components.
Goal: `docker-compose up` starts db + ollama + backend container (even if backend exits immediately with no app).

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `docker-compose.yml` | new | Services: db (pgvector/pgvector:pg16), ollama, backend. Volumes, ports, env_file, depends_on. |
| `.env.example` | new | All required env vars with placeholder values. No real secrets. |
| `.gitignore` | new | Python, Node, .env, __pycache__, .venv, dist, uv.lock optional |
| `backend/Dockerfile` | new | FROM python:3.12-slim. Install uv. COPY pyproject.toml. RUN uv sync. CMD uvicorn placeholder. |
| `README.md` | new | Project name, one-line description, quick-start (docker-compose up + seed). |

---

## docker-compose.yml Services

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U manifesto"]
      interval: 5s
      retries: 5

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
    volumes: [./backend:/app]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
  ollama_data:
```

---

## .env.example Contents

```
DATABASE_URL=postgresql+asyncpg://manifesto:manifesto@db:5432/manifesto
SECRET_KEY=changeme-generate-a-real-secret-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OLLAMA_BASE_URL=http://ollama:11434
OPENAI_API_KEY=
```

---

## Git Setup

Initialize the git repository and wire the pre-commit check as a real git hook:

```bash
git init
cp hooks/pre_commit_check.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Also create an initial `.gitignore` before the first commit so no secrets or build artifacts slip in.

---

## Done When

- [ ] `docker-compose up` starts without errors (backend may exit — no app yet)
- [ ] `db` container passes healthcheck
- [ ] `.env.example` contains all vars referenced in compose
- [ ] `backend/Dockerfile` builds successfully with `docker build ./backend`
- [ ] `git init` done, `.git/hooks/pre-commit` installed and executable
- [ ] `git status` shows only tracked files — no `.env`, no `__pycache__`, no `node_modules`

---

## Handoffs Out

→ Rex (C02): `DATABASE_URL` format is `postgresql+asyncpg://` — asyncpg driver, not psycopg2.
→ Rex (C02): Backend volume mounts `./backend:/app` — working dir inside container is `/app`.
→ Rex (C02): `uv sync` is the install command in Dockerfile — use `pyproject.toml`, not `requirements.txt`.
