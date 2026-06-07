# Smoke Test Results — Commit 21 (`integration-smoke`)

**Date:** 2026-06-07
**Commit hash:** `8da1682`
**Run by:** Adam (DevOps)
**Stack:** `docker compose up -d` (db, ollama, backend) + frontend `npm run dev` (Vite)

---

## Infrastructure

| Check | Result | Notes |
|---|---|---|
| `docker-compose up` starts without errors | ✅ PASS | All three services (`db`, `ollama`, `backend`) reported `Started`/`Healthy` with no compose-level errors. |
| `db` container passes healthcheck within 30 seconds | ✅ PASS | `pg_isready` healthcheck reported `healthy` well within the 30s window (compose reported `db ... Healthy` immediately after `Waiting`). |
| `backend` container starts and stays running (no crash loop) | ✅ PASS (with note) | Container is `Up`/`running`, `GET /` and `/docs` respond. **Note:** backend logs show one `WatchfilesRustInternalError: error in underlying watcher: IO error for operation on /app/uv.lock: Input/output error (os error 5)` event that triggered a reloader restart at some point in the container's history (likely related to the bind-mount `./backend:/app` on Windows/Docker Desktop and `uv.lock` file-watching). The server recovered automatically and is currently stable — this is **not** a crash loop, but is worth noting as a potential dev-experience flake on Windows hosts with `--reload`. |
| `ollama` container starts (no need to pull models yet) | ✅ PASS | Container `Up`, `/bin/ollama serve` running, port 11434 published. No models pulled (per spec, not required). |

---

## Backend

| Check | Result | Notes |
|---|---|---|
| `GET /` returns `{"status": "ok"}` | ✅ PASS | Returned exactly `{"status":"ok"}`. |
| `GET /docs` shows FastAPI OpenAPI UI with all routes listed | ✅ PASS | `GET /docs` returned HTTP 200 (Swagger UI). |
| `alembic upgrade head` runs clean (inside backend container) | ✅ PASS | Ran via `uv run alembic upgrade head` — no errors; `alembic current` / `alembic heads` both confirm `0001_initial (head)`, i.e. DB is already at head (migrations previously applied, idempotent re-run is clean). |
| `python seed.py` runs clean (inside backend container) | ✅ PASS | Ran via `uv run python seed.py` — output: `Seed skipped — user already exists` (idempotent; admin user was already present from a prior run). |

---

## Auth

| Check | Result | Notes |
|---|---|---|
| `POST /auth/login` with `admin@manifesto.local` / `admin123` returns valid JWT | ✅ PASS | Returned `{"access_token": "<JWT>", "token_type": "bearer"}`. JWT decodes to `role: admin`, includes `exp`. |
| `GET /api/v1/vendors` with valid manager/admin token returns `[]` | ⚠️ PASS-WITH-DEVIATION | HTTP 200 returned for both an admin token and a freshly-created manager token, confirming the auth/authorization mechanism works correctly for this route. **However**, the body was **not** `[]` — it returned one existing vendor record (`"Updated Vendor"`, created `2026-06-05`), left over from earlier development/testing against this same persisted `postgres_data` volume. This is a **data-state** discrepancy, not an auth/route failure — the endpoint itself behaves correctly. Document for awareness; not a functional bug. |
| `GET /api/v1/vendors` with no token returns 401 | ✅ PASS | Returned HTTP 401 `{"detail":"Not authenticated"}`. |
| `GET /api/v1/admin/users` with manager token returns 403 | ✅ PASS | No manager user existed in seed data, so Adam created one (`manager.smoke@manifesto.local` / role `manager`) via the admin-authenticated `POST /api/v1/admin/users` endpoint (HTTP 201), then logged in as that user to obtain a manager JWT. `GET /api/v1/admin/users` with that token returned HTTP 403 `{"detail":"Insufficient permissions"}` — correct. |
| `GET /api/v1/admin/users` with admin token returns the seed user | ✅ PASS | Returned HTTP 200 with a list including `admin@manifesto.local` (role `admin`, `is_active: true`). |

> **Note on manager-role testing:** The seed script (`backend/seed.py`) only creates the `admin@manifesto.local` user — there is no seeded manager account. Adam created a throwaway manager user (`manager.smoke@manifesto.local`) via the admin user-management endpoint specifically to exercise the manager-role checks above. This user remains in the `users` table after this test run; Eran/Claude may want to remove it or leave it as a convenience fixture for future manual testing.

---

## Stub routes

| Check | Result | Notes |
|---|---|---|
| `POST /api/v1/chat/conversations` returns 501 | ✅ PASS | Returned HTTP 501 `{"detail":"Not implemented"}`. |
| `POST /api/v1/documents` returns 501 | ✅ PASS | Returned HTTP 501 `{"detail":"Not implemented"}`. |

---

## Frontend

| Check | Result | Notes |
|---|---|---|
| `npm run dev` starts without errors | ✅ PASS | Vite v5.4.21 started cleanly in 514ms, served on `http://localhost:5173/`. `GET /` and `GET /login` both returned HTTP 200 from the dev server. |
| Browser: `/login` renders the login form | ⛔ NOT VERIFIED | Adam does not have browser/devtools-driving capability in this session. The dev server serves the route (HTTP 200), but actual DOM rendering of the login form was not visually/programmatically confirmed. **Manual check needed:** open `http://localhost:5173/login` in a browser and confirm the login form (email + password fields, submit button) renders. |
| Browser: login with seed credentials redirects to `/dashboard` | ❌ FAIL | Eran tested this manually: submitting valid credentials does not log in. **Root cause confirmed via curl:** `frontend/src/api/auth.ts` (`loginApi`, built C17) POSTs `application/x-www-form-urlencoded` with fields `username`/`password`, but `backend/app/api/v1/auth.py` + `backend/app/schemas/auth.py` (`LoginRequest`, built C10, matches its spec exactly) expects a **JSON** body `{"email": "...", "password": "..."}`. The mismatched request returns **HTTP 422** (`"Input should be a valid dictionary or object to extract fields from"`), which `Login.tsx`'s catch-block renders as the generic "Something went wrong. Please try again." — not the 401 "Invalid email or password" the spec describes. Confirmed the backend is correct and reachable: re-sending the *same* credentials as JSON with `email`/`password` keys returns `200` with a valid `{access_token, token_type: "bearer"}`. **This is a contract mismatch introduced in C17** (the spec only fixed `loginApi`'s function signature, not its wire format/field names) — fix belongs in `frontend/src/api/auth.ts` (Aria's domain): switch to `Content-Type: application/json` with `{ email, password }`. |
| Browser: `/dashboard` shows "Coming soon" placeholder | ⛔ BLOCKED — not verifiable | Cannot be reached without a successful login (see failure above). Once the C17/C10 contract mismatch is fixed, re-check: after logging in, confirm `/dashboard` renders a "Coming soon" placeholder. |
| Browser: navigating to `/admin` without admin role redirects | ⛔ BLOCKED — not verifiable | Cannot be reached without a successful login (see failure above). Once fixed, re-check: log in as a non-admin user (e.g. `manager.smoke@manifesto.local` / `manager123`, created during this test) and confirm navigating to `/admin` redirects away rather than rendering the admin page. |

---

## Summary

- **Pass:** 15
- **Pass-with-deviation (functionally correct, data-state note):** 1 (`GET /api/v1/vendors` returns non-empty list due to pre-existing data in the persisted volume, not `[]`)
- **Fail:** 1 — login from the UI is broken end-to-end (see root cause below)
- **Blocked / not independently verifiable:** 2 — both downstream of the login failure (`/dashboard` placeholder, `/admin` redirect)
- **Not verified (requires browser-driving capability not available to Adam):** 1 — `/login` form rendering (independent of the login failure; dev server confirmed serving the route with HTTP 200)

### ❌ Failure — login is broken (C17/C10 contract mismatch)

`POST /auth/login` cannot succeed from the deployed frontend. `loginApi` (built in C17, `frontend/src/api/auth.ts`) sends `application/x-www-form-urlencoded` with `username`/`password` fields; the backend's `LoginRequest` schema (built in C10, `backend/app/schemas/auth.py`, matches its spec exactly) requires a JSON body with `email`/`password` fields. The mismatched request returns HTTP 422, surfaced to the user as a generic "Something went wrong" message instead of a working login.

Confirmed via direct curl against the running backend:
- form-urlencoded `username=...&password=...` → `422 {"detail":[{"type":"model_attributes_type",...,"msg":"Input should be a valid dictionary or object to extract fields from"}]}`
- JSON `{"email": "admin@manifesto.local", "password": "admin123"}` → `200 {"access_token": "...", "token_type": "bearer"}`

**This is a scope/contract gap from C17** — that spec fixed `loginApi`'s function *signature* (`loginApi(email, password) → TokenResponse`) but never specified the wire format or field names, so Aria built it against the common FastAPI `OAuth2PasswordRequestForm` convention while Rex's C10 backend (built correctly per its own spec) used a plain JSON `email`/`password` schema. **Fix belongs in `frontend/src/api/auth.ts`** (Aria's domain — the backend is correct and should not change): switch to `Content-Type: application/json` with body `{ email, password }`.

Per the C21 spec ("If Checks Fail — do not fix inline... each failure becomes a new commit inserted after C21"), this requires its own fix-commit before Phase 1 is declared complete.

### Recommended follow-ups (not failures, just notes for awareness)
1. Insert a fix-commit (Aria, `frontend/src/api/auth.ts`) to correct `loginApi`'s request format to JSON `{ email, password }`; re-run the three blocked/failed browser checks afterward.
2. Independently verify `/login` form rendering (the one remaining "not verified" item — unaffected by the login bug, dev server confirmed serving the route).
3. Consider whether the `WatchfilesRustInternalError` on `uv.lock` (seen once in backend logs) needs investigation — it self-recovered, but repeated occurrences could cause dev friction on Windows + Docker Desktop bind mounts.
4. Decide whether to keep or remove the throwaway `manager.smoke@manifesto.local` test user created during this run (useful for the manual `/admin` redirect re-check above).
5. The `vendors` table already contains a record from prior development testing — fine for a dev DB, just noting that a "fresh" `[]` response should not be expected against this persisted volume.
