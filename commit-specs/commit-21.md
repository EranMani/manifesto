# Commit 21 — `integration-smoke` · Adam

**Phase:** 1G — Integration Verification
**Assignee:** Adam (DevOps)
**Depends on:** C20 (login-page) — full stack must be built before verification

---

## context

```
tier0:
  - .claude/agents/adam.md (Current State header only — first 50 lines)

tier1:
  - docker-compose.yml     # to know service names and ports for curl commands
  - backend/seed.py        # to know the correct run command

tier2: []   # SMOKE_TEST_RESULTS.md is a new file

forbidden:
  - backend/app/           # verification only — do not edit application code
  - frontend/src/          # verification only — do not edit frontend code
  - backend/alembic/       # do not run migrations; they should already be applied

estimated_reads: 2
estimated_edits: 1   # SMOKE_TEST_RESULTS.md (new)
fits_single_agent: true
```

---

## What

Verify the assembled Phase 1 stack works end-to-end. This is a verification commit, not a coding commit.
Adam runs each check against the live docker-compose stack and documents results.
If a check fails, it becomes its own fix commit before Phase 1 is declared done.

---

## Checklist

### Infrastructure
- [ ] `docker-compose up` starts without errors
- [ ] `db` container passes healthcheck within 30 seconds
- [ ] `backend` container starts and stays running (no crash loop)
- [ ] `ollama` container starts (no need to pull models yet)

### Backend
- [ ] `GET /` returns `{"status": "ok"}`
- [ ] `GET /docs` shows FastAPI OpenAPI UI with all routes listed
- [ ] `alembic upgrade head` runs clean (run inside backend container)
- [ ] `python seed.py` runs clean (run inside backend container)

### Auth
- [ ] `POST /auth/login` with `admin@manifesto.local` / `admin123` returns valid JWT
- [ ] `GET /api/v1/vendors` with valid manager/admin token returns `[]`
- [ ] `GET /api/v1/vendors` with no token returns 401
- [ ] `GET /api/v1/admin/users` with manager token returns 403
- [ ] `GET /api/v1/admin/users` with admin token returns the seed user

### Stub routes
- [ ] `POST /api/v1/chat/conversations` returns 501
- [ ] `POST /api/v1/documents` returns 501

### Frontend
- [ ] `npm run dev` starts without errors
- [ ] Browser: `/login` renders the login form
- [ ] Browser: login with seed credentials redirects to `/dashboard`
- [ ] Browser: `/dashboard` shows "Coming soon" placeholder
- [ ] Browser: navigating to `/admin` without admin role redirects

---

## Deliverable

A `SMOKE_TEST_RESULTS.md` file at project root documenting:
- Date and commit hash
- Pass/fail for each checklist item
- Any failures with description (these become fix commits)

---

## If Checks Fail

Do not fix inline. Document the failure in `SMOKE_TEST_RESULTS.md` and surface to Claude/Eran.
Each failure becomes a new commit inserted after C21 before Phase 1 is closed.

---

## Done When

- [ ] All checklist items pass
- [ ] `SMOKE_TEST_RESULTS.md` written with full results
- [ ] Phase 1 declared complete in `project-state.json`
