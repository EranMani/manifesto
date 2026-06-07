# Aria — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + React + Vite + Tailwind

---

## Current State
*Last updated: Commit 22 · 2026-06-07*

**Last completed:** C22 `fix-login-request-format` ✅
**Currently active:** none
**Blocked by:** none

**Key Decision (C22):** Replaced the `URLSearchParams` / `application/x-www-form-urlencoded` body in `loginApi` with a plain JSON object `{ email, password }`, matching the backend's `LoginRequest` schema (`{email, password}`). Axios sets `Content-Type: application/json` automatically for plain object bodies, so the explicit header was removed too.

**Key Decision (C20):** Derived `User.name` from the email's local part (text before `@`), splitting on `.`/`_`/`-` and title-casing each segment (e.g. `admin@manifesto.local` → `"Admin"`). The JWT payload only carries `sub`/`role`, not a display name, so the email is the only client-side signal available at login time.

**Open Handoffs — Outbound:**
- (none — C20 closes the loop opened in C19)

**Open Handoffs — Inbound:**
- ← Rex/C10: Token format is `{access_token: string, token_type: "bearer"}`. ✅ Consumed — auth store and Axios interceptor implemented.

**Key Interfaces I Own:**
- `frontend/vite.config.ts` — proxy to backend :8000
- `frontend/src/App.tsx` — root component (routing added C18)

**Decisions Other Agents Must Know:**
- postcss.config.js added (required by Tailwind v3 + Vite — not in spec but necessary for build)

**Scope Overflows Pre-Built:**
- (none)

**Archive Reference:**
No archived sessions yet.

---

## 📋 Replan Notice — 2026-06-07

The commit plan has been updated. Here is what changed for you:

What was removed: nothing — pure addition after C22.
What was added: Phase 2 "Policy RAG" — 10 new commits (C23-C32) per `manifesto-spec.md` §Phase 2.
What changed in your sequence: you own the chat frontend — C30 (`policy-chat-ui`, the chat shell
and SSE streaming), C31 (`conversation-sidebar-ui`, history sidebar), and C32 (`citations-ui`,
source citations). You'll be building against Rex's new SSE endpoint (`POST /api/v1/chat/policy`,
landing in C28) and conversation history endpoints (C29) — read those handoffs when you reach C30.
Your next commit is now: Commit 30 `policy-chat-ui` (after C23-C29 land).

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | C03 frontend-scaffold | ✅ Done | Added postcss.config.js — required by Tailwind v3; omitting it breaks build |
| 02 | C17 auth-store-and-client | ✅ Done | `useAuthStore.getState()` used in Axios interceptors (not hooks) — correct pattern for non-React context |
| 03 | C18 protected-route | ✅ Done | `ProtectedRoute` uses `<Outlet />` pattern; role check + token check both redirect to /login; fixed pre-existing tsconfig missing vite/client types |
| 04 | C19 placeholder-pages | ✅ Done (Claude direct write — spec fully prescriptive) | VendorList.tsx used as component name; imported as `VendorList` in App.tsx replacing `Vendors` stub |
| 05 | C20 login-page | ✅ Done | Derived `User.name` by title-casing the email local-part (split on `.`/`_`/`-`); JWT only has `sub`/`role`, no display name |
| 06 | C22 fix-login-request-format | ✅ Done | Replaced form-urlencoded `username`/`password` body with JSON `{ email, password }` to match backend's `LoginRequest` schema |

---

## Session 05 — Commit 20: `login-page`

**Date:** 2026-06-07
**Status:** ✅ Done

### Task Brief
Build the real `Login` page at `frontend/src/pages/Login.tsx`, replacing the inline stub in `App.tsx`. Wire it to `loginApi`, `useAuthStore`, JWT decode, and navigation.

### Approach
Phase 1 (reads): read `App.tsx`, `store/auth.ts`, `api/auth.ts`, and `Dashboard.tsx` (for styling conventions) — interfaces were already given verbatim in the brief, so minimal reading needed.
Phase 2 (writes): created `Login.tsx` (controlled form, Tailwind card layout, loading/error states, JWT decode via `atob`, redirect-if-authenticated via `<Navigate>`); swapped the inline stub for a real default import in `App.tsx` (2-line change: import + stub removal). Ran `npx tsc --noEmit` (clean) and `npx vite build` (clean, 110 modules, built in 2.75s).

### Decisions Made
- **`User.name` derivation:** the JWT payload (`{sub, role}`) carries no display name, so I derived it from the email's local part — split on `.`/`_`/`-`, title-case each segment, join with spaces. `admin@manifesto.local` → `"Admin"`. This is a sensible, deterministic placeholder until the backend returns a real `name` claim or profile endpoint.
- Used `isAxiosError` from `axios` to discriminate 401 (invalid credentials) vs. no-response (network error) vs. other errors, per the spec's three error-message branches.
- Used `<Navigate to="/dashboard" replace />` for the already-authenticated guard (declarative, consistent with `RootRedirect` in `App.tsx`) rather than an imperative `useEffect` + `navigate`.

### Issues Found Mid-Task
None — interfaces matched the brief exactly; no ambiguity required extra reads.

### Self-Review Checklist
- [x] No `any` types (JWT payload typed via `JwtPayload` interface)
- [x] No secrets in staged files
- [x] TypeScript strict mode — `npx tsc --noEmit` clean
- [x] `npx vite build` exits 0 (dist/ produced, built in 2.75s)
- [x] Tailwind-only styling, no inline styles / CSS modules

### Scope Overflow Check
No scope overflow. Only `Login.tsx` (new) and `App.tsx` (2-line import/stub swap) touched, per constraints.

### Documentation Flags for Claude
**ARCHITECTURE.md:** Login page implemented — controlled form posts via `loginApi`, decodes JWT client-side (`sub`/`role`), derives display name from email local-part, persists to `useAuthStore`, redirects to `/dashboard`. Already-authenticated users are redirected away from `/login`.

---

## Session 01 — Commit 03: `frontend-scaffold`

**Date:** 2026-06-04
**Status:** ✅ Done

### Task Brief
Initialize React 18 + Vite + TypeScript (strict) + Tailwind CSS frontend scaffold. No pages, no components, no API calls. `npm run dev` must render a blank white page; `npm run build` must produce `dist/`.

### Approach
Phase 1 (reads): confirmed no `frontend/` directory existed; read `project-state.json` and `docker-compose.yml` to confirm backend port (8000).
Phase 2 (writes): created all 9 spec files plus `postcss.config.js` (required by Tailwind v3); ran `npm install`; ran `npm run build`.

### Decisions Made
- Added `postcss.config.js` alongside the spec files — Tailwind v3 requires PostCSS config for Vite to process CSS at build time. Without it, `npm run build` would succeed but Tailwind directives would not be processed. This is a mechanical requirement of the stack, not a design choice.
- `tsconfig.json` uses `"moduleResolution": "bundler"` and `"allowImportingTsExtensions": true` — standard Vite + TypeScript setup for strict mode with no emit.

### Issues Found Mid-Task
- `postcss.config.js` absent from spec but required for Tailwind v3 + Vite. Added without hesitation — it is a zero-scope-risk file.

### Self-Review Checklist
- [x] No `any` types
- [x] No secrets in staged files
- [x] TypeScript strict mode on (`"strict": true` in tsconfig.json)
- [x] npm install exits 0 (165 packages audited, up to date)
- [x] npm run build exits 0 (dist/ produced, built in 961ms)

### Scope Overflow Check
No scope overflow. `postcss.config.js` is a mandatory config file for the declared stack (Tailwind v3 + Vite), not a feature addition.

### Documentation Flags for Claude
**ARCHITECTURE.md:**
- Frontend scaffold — React 18 + Vite + TypeScript strict initialized; Tailwind CSS v3 with PostCSS; Vite proxy routes /api and /auth to backend :8000; entry point src/main.tsx renders App into #root

**DECISIONS.md:**
- postcss.config.js added to frontend/ — required by Tailwind CSS v3 for Vite to process @tailwind directives at build time; absent from spec but zero-risk mandatory config for the declared stack

---

## Session 02 — Commit 17: `auth-store-and-client`

**Date:** 2026-06-06
**Status:** ✅ Done

### Task Brief
Create three pure state/API layer files — no UI, no pages, no components:
- `frontend/src/store/auth.ts` — Zustand auth slice
- `frontend/src/api/client.ts` — Axios instance with JWT interceptor and 401 handler
- `frontend/src/api/auth.ts` — `loginApi` function

### Approach
Phase 1 (reads): verified `frontend/src/` directory structure via Glob — confirmed scaffold files exist, `store/` and `api/` subdirectories absent (need to create).
Phase 2 (writes): created all 3 files per spec; updated worklog.

### Decisions Made
- Used `useAuthStore.getState()` inside Axios interceptors (not `useAuthStore()` hook) — interceptors run outside React component trees, so the hook form would throw. `.getState()` is the correct Zustand pattern for non-React contexts such as network interceptors.
- `loginApi` uses `URLSearchParams` for the form body — FastAPI's `OAuth2PasswordRequestForm` expects `application/x-www-form-urlencoded` with field `username` (not `email`). This is consistent with the spec note.
- `user.name` defaults to `""` if the JWT payload `name` field is absent — per spec instruction.

### Issues Found Mid-Task
- None. Spec was complete and unambiguous.

### Self-Review Checklist
- [x] No `any` types — all types explicit (`string`, `User`, `AuthState`, `TokenResponse`)
- [x] No secrets in staged files
- [x] TypeScript strict mode compatible — no implicit `any`, no untyped props
- [x] No localStorage usage — Zustand in-memory only
- [x] No jwt library — `atob()` decode used per standards
- [x] `useAuthStore` returns `{ token, user, login, logout }` ✅
- [x] `loginApi` function exists and is typed ✅
- [x] Axios interceptor attaches token header when token is set ✅
- [x] Axios interceptor calls logout and redirects on 401 ✅

### Scope Overflow Check
No scope overflow. Exactly 3 files created, no existing files modified.

### Handoffs Out
- → Aria (self, C18): `useAuthStore` is the auth source of truth for `ProtectedRoute`. Check `user.role` from the store.
- → Aria (self, C20): `loginApi` is the function Login page calls. On success, call `store.login(token, decodedUser)` then navigate to `/dashboard`.

### Documentation Flags for Claude
**ARCHITECTURE.md:**
- Auth layer added — Zustand in-memory auth store (`store/auth.ts`); Axios instance with Bearer token interceptor and 401→logout redirect (`api/client.ts`); typed `loginApi` function posting OAuth2 form to `/auth/login` (`api/auth.ts`)

**DECISIONS.md:**
- `useAuthStore.getState()` used inside Axios interceptors — correct Zustand pattern for non-React contexts; hook form (`useAuthStore()`) is React-only and would throw outside component trees

---

## Session 03 — Commit 18: `protected-route`

**Date:** 2026-06-06
**Status:** ✅ Done

### Task Brief
Build role-based route guard and wire up full React Router v6 routing:
- `frontend/src/components/ProtectedRoute.tsx` — role-based guard using `<Outlet />`
- `frontend/src/App.tsx` — full router with all 8 route paths, inline page stubs

### Approach
Phase 1 (reads): confirmed `frontend/src/` structure; verified `react-router-dom ^6.23.0` in package.json — no install needed.
Phase 2 (writes): created `ProtectedRoute.tsx`; rewrote `App.tsx` with full route table; added `"types": ["vite/client"]` to `tsconfig.json` to fix pre-existing `import.meta.env` error from C17; confirmed `npx tsc --noEmit` exits clean (0 errors).

### Decisions Made
- `ProtectedRoute` redirects to `/login` for both missing token and unauthorized role — not a separate `/unauthorized` route. Spec says "redirect to /login (or /unauthorized)"; keeping a single error destination avoids leaking route existence to unauthorized users and simplifies the Login page implementation.
- `RootRedirect` is a small standalone component (not inline JSX) so it can call the `useAuthStore` hook — hooks cannot be called in the render body of `App` directly without `RootRedirect` being its own component.
- `tsconfig.json` `"types": ["vite/client"]` added — fixes pre-existing `import.meta.env` error in `api/client.ts` (C17 gap). This is the standard Vite TypeScript fix; no functional change.
- Grouped routes by role set (manager+admin vs manager+admin+employee vs admin-only) rather than repeating `allowedRoles` on each child route — cleaner and avoids drift if roles change.

### Issues Found Mid-Task
- Pre-existing TypeScript error in `api/client.ts`: `Property 'env' does not exist on type 'ImportMeta'` — caused by missing Vite client types in `tsconfig.json`. Fixed by adding `"types": ["vite/client"]`. Not a C18 regression — present since C17.

### Self-Review Checklist
- [x] No `any` types — `ProtectedRouteProps` typed, all store selectors typed
- [x] No secrets in staged files
- [x] TypeScript strict mode — `npx tsc --noEmit` exits 0
- [x] `ProtectedRoute` uses `<Outlet />` (not `{children}`) — correct React Router v6 pattern
- [x] All 8 route paths from spec table present in App.tsx
- [x] No imports from `frontend/src/pages/` — inline stubs only
- [x] No `backend/` files touched

### Scope Overflow Check
- `tsconfig.json` modification: strictly necessary to fix a TypeScript compile error that would block the build gate. Not a feature addition.

### Handoffs Out
- → Aria (self, C19 placeholder-pages): Page stubs are currently inline in `App.tsx` as anonymous arrow functions. When real page components are created in `src/pages/`, replace the inline stubs with named imports.
- → Aria (self, C20 login-page): `loginApi` is the function the Login page calls. On success: decode JWT with `atob()`, call `store.login(token, decodedUser)`, then navigate to `/dashboard`.

### Documentation Flags for Claude
**ARCHITECTURE.md:**
- React Router v6 wiring complete — `BrowserRouter` + `Routes` in `App.tsx`; `ProtectedRoute` wraps all authenticated routes with role-based access; root `/` redirects based on auth state; 8 route paths defined matching spec

**DECISIONS.md:**
- `ProtectedRoute` redirects unauthorized roles to `/login` (not `/unauthorized`) — avoids leaking route existence to unauthorized users; simplifies Login page implementation
- `"types": ["vite/client"]` added to `tsconfig.json` — standard fix for `import.meta.env` type resolution in Vite projects; was missing since C17

---

## Session 06 — Commit 22: `fix-login-request-format`

**Date:** 2026-06-07
**Status:** ✅ Done

### Task Brief
Adam's C21 integration smoke test found login broken end-to-end: `loginApi` (built in C17) sent the request as `application/x-www-form-urlencoded` with `username`/`password` fields, but the backend's `LoginRequest` schema (`backend/app/schemas/auth.py`, read-only reference) requires a JSON body `{ email, password }`. The form-encoded request returned `422`.

### Approach
Phase 1 (read): re-read `frontend/src/api/auth.ts` to confirm the current (broken) state matched the brief exactly.
Phase 2 (write + test): replaced the `URLSearchParams` body construction and explicit `Content-Type: application/x-www-form-urlencoded` header with a single-line JSON object `{ email, password }` passed directly to `apiClient.post`. Axios infers `Content-Type: application/json` for plain object bodies, so no header override was needed. Ran `npx tsc --noEmit` — clean, no errors.

### Final Function
```typescript
export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', { email, password })
  return response.data
}
```

### Decisions Made
- None beyond the prescribed fix — the brief fully specified the replacement code; no ambiguity.

### Issues Found Mid-Task
None.

### Self-Review Checklist
- [x] No `any` types
- [x] No secrets in staged files
- [x] TypeScript strict mode — `npx tsc --noEmit` exits 0, no output
- [x] Function signature `loginApi(email, password) → TokenResponse` unchanged
- [x] `Login.tsx` not touched (no changes required)
- [x] `TokenResponse` interface unchanged
- [x] No `backend/` files touched

### Scope Overflow Check
No scope overflow. Only `frontend/src/api/auth.ts` edited — single function body replaced, exactly as specified.

### Handoffs Out
- (none — this closes the loop opened by Adam's C21 smoke-test finding; login should now work end-to-end with the JSON `{ email, password }` body matching the backend's `LoginRequest` schema)

### Documentation Flags for Claude
**ARCHITECTURE.md:** No update needed — this is a bug fix that brings the existing implementation in line with the documented contract (backend `LoginRequest` schema), not a new pattern or component.
