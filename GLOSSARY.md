# GLOSSARY.md — Manifesto

> Maintained by Claude. New terms are added when first introduced — not retroactively.
> Last updated: 2026-06-04 (C02)

---

## Terms

### asyncpg
PostgreSQL async driver for Python. Used via the `postgresql+asyncpg://` connection string prefix. Chosen over psycopg2 because FastAPI uses async I/O — a sync driver would block the event loop. See also: `DATABASE_URL`.

### DATABASE_URL
The full PostgreSQL connection string used by SQLAlchemy. Format in this project: `postgresql+asyncpg://manifesto:manifesto@db:5432/manifesto`. The `db` hostname resolves to the Docker Compose `db` service — does not work outside the container network.

### pgvector
PostgreSQL extension for storing and querying vector embeddings. Enables similarity search directly in the database without a separate vector store. Docker image: `pgvector/pgvector:pg16`.

### uv
Rust-based Python package manager. Replaces pip + requirements.txt. Install command: `uv sync` (reads from `pyproject.toml`). Add packages with `uv add <package>`. Significantly faster than pip. See D02.

### uvicorn
ASGI server that runs the FastAPI application. Launched with `--reload` in dev so file changes restart automatically. Bind mount `./backend:/app` makes reloads instant without rebuilding the container.

### Ollama
Local LLM serving layer. Runs as a Docker service (`ollama/ollama`). Exposes an API at `http://ollama:11434` inside the Docker network. Used to serve embedding and generation models locally without cloud API calls.

### structlog
Python structured logging library. Produces log output as key-value pairs or JSON instead of plain text — makes logs machine-parseable and searchable. Imported in `main.py` as `logger = structlog.get_logger()`. Added in C02.

### commit-protocol
The ordered build sequence for Phase 1. Each entry is one atomic unit of work with one owner and one test gate. No commit is made without Eran's approval. Stored in `commit-protocol.md` (index) and `commit-specs/` (full specs).

### Gate wave
The batch of reviewer agents (Viktor, Sage, Mira) that runs after every 5th commit. Viktor always runs. Sage runs conditionally (auth, secrets, external API commits). Mira runs conditionally (user-facing behavior changes). See AGENTS.md.

### handoff
A structured note passed between agents at commit boundaries. Written by the outgoing agent in their worklog; received by the next agent before they begin. Handoffs carry decisions, interface contracts, or constraints that aren't visible from the code alone.

---

*This document is updated by Claude when a new term is introduced that would be ambiguous or non-obvious to a reader unfamiliar with this project's conventions.*
