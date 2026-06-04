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

---

## Services

| Service  | Port  | Description              |
|----------|-------|--------------------------|
| backend  | 8000  | FastAPI application      |
| db       | 5432  | PostgreSQL + pgvector    |
| ollama   | 11434 | Local LLM inference      |
