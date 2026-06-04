# Adam — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + React + Vite + Tailwind

---

## Current State
*Last updated: Commit 01 · 2026-06-04*

**Last completed:** Commit 01 `project-scaffold` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- → Rex (C02): DATABASE_URL is `postgresql+asyncpg://` — asyncpg driver, not psycopg2
- → Rex (C02): Backend volume `./backend:/app` — working dir inside container is `/app`
- → Rex (C02): `uv sync` installs deps — use `pyproject.toml`, not `requirements.txt`

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
- `docker-compose.yml`: 3 services (db, ollama, backend) + named volumes + db healthcheck
- `backend/Dockerfile`: python:3.12-slim + uv; build will fail until Rex creates pyproject.toml in C02
- `.env.example`: 7 vars documented (DATABASE_URL, SECRET_KEY, ALGORITHM, token expiry × 2, OLLAMA_BASE_URL, OPENAI_API_KEY)

**Decisions Other Agents Must Know:**
- asyncpg driver chosen (`postgresql+asyncpg://`) — matches pgvector/pgvector:pg16 image
- Git hook installed as a sh wrapper at `.git/hooks/pre-commit` (calls `hooks/pre_commit_check.py` via `python`) — Windows Git for Windows requires a sh-executable wrapper, not a bare .py file

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | C01: project-scaffold | ✅ Done | asyncpg driver in DATABASE_URL; sh wrapper for git hook on Windows |

---

## Session 01 — Commit 01: `project-scaffold`
*2026-06-04*

**Approach:** Two-phase execution. Phase 1: read existing state (directory listing, `.git/hooks` contents, `hooks/pre_commit_check.py` shebang). Phase 2: all writes in sequence.

**Files created:**
- `docker-compose.yml` — 3 services, named volumes, db healthcheck
- `.env.example` — 7 vars, no real secrets
- `.gitignore` — Python + Node + OS + IDE ignores; `.env` on line 2
- `backend/Dockerfile` — python:3.12-slim + uv; pyproject.toml COPY will fail until C02 (expected)
- `README.md` — project description + quick-start + service table (27 lines)
- `.claude/agents/logs/adam-worklog.md` — this file

**Git hook decision:** `hooks/pre_commit_check.py` has a `#!/usr/bin/env python3` shebang. On Windows, Git for Windows runs hooks through its bundled `sh`. A bare Python file with a shebang is not reliably executable on Windows because `python3` is not always on PATH in Git's sh environment. Created `.git/hooks/pre-commit` as a sh wrapper calling `python hooks/pre_commit_check.py` explicitly — more portable on Windows.

**Issues / scope notes:**
- `backend/` directory created (needed to place Dockerfile); no app code added — stays empty pending C02
- No `scripts/` directory created — not in spec scope for C01; README references `scripts/seed.py` as future step
- `.gitignore` includes `dist/` twice (Python build and Node build artifacts) — deduplicated by context; both are valid entries under their respective sections
