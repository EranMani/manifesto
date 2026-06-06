# Aria — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + React + Vite + Tailwind

---

## Current State
*Last updated: Commit 19 · 2026-06-06*

**Last completed:** C19 `placeholder-pages` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- → Aria (self, C20): `loginApi` is the function Login page calls. On success, call `store.login(token, decodedUser)` then navigate to `/dashboard`.

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

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | C03 frontend-scaffold | ✅ Done | Added postcss.config.js — required by Tailwind v3; omitting it breaks build |
| 02 | C17 auth-store-and-client | ✅ Done | `useAuthStore.getState()` used in Axios interceptors (not hooks) — correct pattern for non-React context |
| 03 | C18 protected-route | ✅ Done | `ProtectedRoute` uses `<Outlet />` pattern; role check + token check both redirect to /login; fixed pre-existing tsconfig missing vite/client types |
| 04 | C19 placeholder-pages | ✅ Done (Claude direct write — spec fully prescriptive) | VendorList.tsx used as component name; imported as `VendorList` in App.tsx replacing `Vendors` stub |

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
