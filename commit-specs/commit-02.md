# Commit 02 — `python-skeleton` · Rex

**Phase:** 1A — Infrastructure Foundation
**Assignee:** Rex (Backend)
**Depends on:** C01 (project-scaffold)
**Parallel with:** C03 (frontend-scaffold) — zero shared files

---

## What

Create the Python backend project skeleton. A bare FastAPI app that starts, registers no routes yet,
and returns `{"status": "ok"}` on `GET /`. All folder structure established. uv configured.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/pyproject.toml` | new | Project metadata, all dependencies, uv config |
| `backend/app/__init__.py` | new | Empty |
| `backend/app/main.py` | new | FastAPI app, CORS middleware, structlog, `GET /` health route. Comment block: `# routers registered below` |
| `backend/app/api/__init__.py` | new | Empty |
| `backend/app/api/v1/__init__.py` | new | Empty |
| `backend/app/core/__init__.py` | new | Empty |
| `backend/app/models/__init__.py` | new | Empty |
| `backend/app/schemas/__init__.py` | new | Empty |
| `backend/app/services/__init__.py` | new | Empty |
| `backend/app/dependencies.py` | new | Empty file — stubs added in C09 |

---

## pyproject.toml Dependencies

```toml
[project]
name = "manifesto"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic-settings>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "pgvector>=0.2.0",
    "pymupdf>=1.24.0",
    "python-docx>=1.1.0",
    "structlog>=24.1.0",
    "python-multipart>=0.0.9",
]
```

---

## main.py Structure

```python
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = structlog.get_logger()

app = FastAPI(title="Manifesto", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health():
    return {"status": "ok"}

# routers registered below
```

---

## Done When

- [ ] `uv sync` runs without errors inside `backend/`
- [ ] `uvicorn app.main:app` starts without import errors
- [ ] `GET /` returns `{"status": "ok"}`
- [ ] All `__init__.py` files exist (folder structure complete)

---

## Handoffs Out

→ Aria (C03): No shared files — frontend scaffold can run in parallel.
→ Rex (C04): `app/main.py` has `# routers registered below` comment — append routers there in future commits.
