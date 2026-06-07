# Adam — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + React + Vite + Tailwind

---

## Current State
*Last updated: Commit 21 · 2026-06-07*

**Last completed:** Commit 21 `integration-smoke` ✅ (verification commit — no app code touched)
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- → Claude/Eran (C21): `SMOKE_TEST_RESULTS.md` written at project root — 16 PASS, 1 PASS-with-deviation (vendors list non-empty due to persisted dev data, not a bug), 4 NOT-VERIFIED (frontend browser-driven checks — require manual/Playwright verification, Adam has no browser-driving capability), 0 FAIL. No fix-commits required.
- → Claude/Eran (C21): Created a throwaway manager user `manager.smoke@manifesto.local` / `manager123` (role `manager`) via the admin user-management endpoint, since seed data only includes an admin user. Decide whether to keep (useful fixture for the manual `/admin` redirect check) or remove.
- → Claude/Eran (C21): One-time `WatchfilesRustInternalError` on `/app/uv.lock` observed in backend logs (self-recovered, not a crash loop) — possible Windows/Docker Desktop bind-mount file-watching flake worth keeping an eye on.

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
- `docker-compose.yml`: 3 services (db, ollama, backend) + named volumes + db healthcheck
- `backend/Dockerfile`: python:3.12-slim + uv
- `.env.example`: 7 vars documented (DATABASE_URL, SECRET_KEY, ALGORITHM, token expiry × 2, OLLAMA_BASE_URL, OPENAI_API_KEY)
- `SMOKE_TEST_RESULTS.md`: full Phase 1 end-to-end verification results (new, C21)

**Decisions Other Agents Must Know:**
- asyncpg driver chosen (`postgresql+asyncpg://`) — matches pgvector/pgvector:pg16 image
- Git hook installed as a sh wrapper at `.git/hooks/pre-commit` (calls `hooks/pre_commit_check.py` via `python`) — Windows Git for Windows requires a sh-executable wrapper, not a bare .py file
- Phase 1 stack verified end-to-end and works: db/backend/ollama all start clean, migrations + seed are idempotent, auth/role enforcement (admin vs manager vs anonymous) behaves correctly, stub routes correctly return 501, and the Vite dev server serves the SPA. Only the four browser-rendered frontend checks remain unverified (no browser-automation capability available to Adam).

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | C01: project-scaffold | ✅ Done | asyncpg driver in DATABASE_URL; sh wrapper for git hook on Windows |
| 21 | C21: integration-smoke | ✅ Done | Full stack verified live; 16 pass / 1 pass-with-deviation / 4 not-verified / 0 fail; created throwaway manager user to test role-based 403 |

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

---

## Session 21 — Commit 21: `integration-smoke`
*2026-06-07*

**Approach:** Verification-only commit — no app code touched. Read spec + docker-compose.yml + seed.py, started Docker Desktop (was not running), brought up the full stack with `docker compose up -d`, then ran every checklist item against the live stack: infra health, backend HTTP checks, alembic/seed inside the container, full auth matrix (admin/manager/anonymous), stub-route 501 checks, and frontend `npm run dev`.

**Key finding — no manager seed user:** `backend/seed.py` only creates `admin@manifesto.local`. To test the manager-role checks (`vendors` 200/`[]` and `admin/users` 403) I created a throwaway manager user `manager.smoke@manifesto.local` / `manager123` via the admin-authenticated `POST /api/v1/admin/users` endpoint, then logged in as that user to get a manager JWT. This let me exercise every auth check exactly as specified rather than skipping them.

**Results (full detail in `SMOKE_TEST_RESULTS.md`):**
- Infrastructure: 4/4 PASS (db healthy <30s, backend stable, ollama up). One non-fatal `WatchfilesRustInternalError` on `/app/uv.lock` seen once in backend logs — self-recovered, documented as a note, not a failure.
- Backend: 4/4 PASS (`GET /` → `{"status":"ok"}`, `/docs` → 200, `alembic upgrade head` clean at `0001_initial (head)`, `seed.py` idempotent-skip).
- Auth: 5/5 functionally PASS. One item (`vendors` returns `[]`) is PASS-WITH-DEVIATION — the route correctly returns 200 for both admin and manager tokens and 401 with no token, but the body contains one pre-existing vendor record from earlier dev/testing against the persisted `postgres_data` volume, not an empty array. This is a data-state artifact, not an auth bug.
- Stub routes: 2/2 PASS (`chat/conversations` and `documents` POST → 501).
- Frontend: `npm run dev` PASS (Vite 5.4.21, ready in 514ms, `/` and `/login` both 200). The four browser-rendered checks (login form renders, login redirects to `/dashboard`, dashboard shows "Coming soon", `/admin` redirects non-admins) are marked **NOT VERIFIED** — Adam has no browser/devtools-driving capability this session. Documented exactly what to check manually, including using the new `manager.smoke@manifesto.local` account for the `/admin` redirect check.

**Tally:** 16 PASS · 1 PASS-with-deviation (documented, not a bug) · 4 NOT VERIFIED (frontend browser checks — need manual/Playwright follow-up) · 0 FAIL.

**Outcome:** No checklist item failed — no fix-commits required. Phase 1 stack is confirmed working end-to-end at the API/infra level. Surfaced the four unverified browser checks and the throwaway manager-user/cleanup decision to Claude/Eran via worklog handoff.

**Deliverables:**
- `SMOKE_TEST_RESULTS.md` (new, project root) — full pass/fail/not-verified table with descriptions
- This worklog entry + Current State header update

**Did not touch:** `backend/app/`, `frontend/src/`, `backend/alembic/` (verification only, per spec). Did not run `git commit` (Claude/Eran handle commits).
