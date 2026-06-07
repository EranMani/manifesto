# Commit 22 — `fix-login-request-format` · Aria

**Phase:** 1G — Integration Verification (fix-commit, inserted after C21 per "If Checks Fail")
**Assignee:** Aria (Frontend)
**Depends on:** C21 (integration-smoke) — this commit exists because C21 found a real failure

---

## context

```
tier0:
  - .claude/agents/aria.md (Current State header only — first 50 lines)

tier1:
  - frontend/src/api/auth.ts       # the file to fix
  - backend/app/schemas/auth.py    # authoritative contract: LoginRequest{email, password} JSON

tier2: []   # no new files

forbidden:
  - backend/                       # backend is correct — do not touch it
  - frontend/src/pages/            # Login.tsx does not need to change — only the API call shape
  - frontend/src/store/

estimated_reads: 2
estimated_edits: 1   # frontend/src/api/auth.ts
fits_single_agent: true
```

---

## What

`SMOKE_TEST_RESULTS.md` (C21) found that login is broken end-to-end: `loginApi` POSTs
`application/x-www-form-urlencoded` with `username`/`password` fields, but the backend's
`LoginRequest` schema (`backend/app/schemas/auth.py`, built in C10 exactly per its spec)
requires a **JSON** body with `email`/`password` fields. The mismatch returns HTTP 422,
surfaced to the user as a generic "Something went wrong" message — login never succeeds.

Confirmed via curl against the live backend:
- form-urlencoded `username=...&password=...` → `422` (`"Input should be a valid dictionary or object..."`)
- JSON `{"email": "...", "password": "..."}` → `200` with a valid `{access_token, token_type}`

**The backend is correct and must not change.** The fix is entirely in `loginApi`.

---

## Files to Modify

| File | Type | Description |
|---|---|---|
| `frontend/src/api/auth.ts` | update | Change `loginApi` request body from form-urlencoded `username`/`password` to JSON `{ email, password }` |

---

## Required Change

Replace the `URLSearchParams`/form-urlencoded request body with a plain JSON object matching
`LoginRequest`:

```typescript
export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', { email, password })
  return response.data
}
```

- Remove the `URLSearchParams` body construction and the explicit
  `Content-Type: application/x-www-form-urlencoded` header — Axios sets
  `Content-Type: application/json` automatically for a plain object body.
- The function signature (`loginApi(email, password) → TokenResponse`) does not change —
  `Login.tsx` requires no changes.

---

## Done When

- [ ] `loginApi` sends a JSON body `{ email, password }` to `POST /auth/login`
- [ ] Login with `admin@manifesto.local` / `admin123` succeeds and redirects to `/dashboard`
- [ ] Login with wrong credentials still shows "Invalid email or password" (401 path unaffected)
- [ ] No TypeScript errors (`tsc`)
- [ ] No console errors in browser

---

## Test Gate

- `cd frontend && npx tsc --noEmit` — must pass clean
- Manual/browser re-check of the three items C21 marked FAIL/BLOCKED:
  - login redirects to `/dashboard`
  - `/dashboard` shows "Coming soon" placeholder
  - non-admin navigating to `/admin` redirects away
- Plus the one still-`NOT VERIFIED` item from C21: `/login` form renders correctly

---

## If This Reveals Further Issues

Do not fix inline beyond the documented scope. Surface to Claude/Eran — another fix-commit
would be inserted before Phase 1 closes.

---

## Handoffs Out

→ Eran/Claude: once merged, re-run the four C21 browser checks (3 blocked/failed + 1 not-verified)
to close out `SMOKE_TEST_RESULTS.md` and clear Phase 1 for completion.
