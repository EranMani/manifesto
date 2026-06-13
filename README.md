# Manifesto

A logistics RAG platform — ingest vendor documents, query them with natural language, return structured answers.

**Stack:** FastAPI + SQLAlchemy + PostgreSQL + pgvector + React + Vite + Tailwind + Ollama

---

## Quick Start

### Prerequisites
- Docker + Docker Compose

### Run

```bash
# Copy env template
cp .env.example .env

# Start all services (db, ollama, backend)
docker-compose up
```

The backend will be available at `http://localhost:8000` once the db health check passes.

### Seed the database

```bash
docker-compose exec backend python scripts/seed.py
```

### Run backend tests

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_backend.ps1
```

Runs the full backend test suite (`uv run pytest tests/`) inside the `backend`
container via `docker compose run --rm`, so the database hostname `db` resolves
correctly. Pass `-CollectOnly` to collect tests without running them.

---

## Services

| Service  | Port  | Description              |
|----------|-------|--------------------------|
| backend  | 8000  | FastAPI application      |
| db       | 5432  | PostgreSQL + pgvector    |
| ollama   | 11434 | Local LLM inference      |
