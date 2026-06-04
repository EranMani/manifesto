# Commit 20 — `login-page` · Aria

**Phase:** 1F — Frontend Core
**Assignee:** Aria (Frontend)
**Depends on:** C19 (placeholder-pages), C10 (auth-route live), C08 (seed credentials exist)

**Viktor + Mira wave runs on this commit (C20 is the 20th commit; Mira triggered by real user interaction).**

---

## What

Implement the Login page with real form logic: POST to `/auth/login`, store token, redirect to dashboard.
This is the only page in Phase 1 with real functionality — it must work correctly.

---

## Files to Create/Modify

| File | Type | Description |
|---|---|---|
| `frontend/src/pages/Login.tsx` | new | Login form, API call, error handling, redirect |

---

## Login.tsx Requirements

- Email + password form fields
- Submit calls `loginApi(email, password)` from `api/auth.ts`
- On success: call `store.login(token, decodedUser)` → navigate to `/dashboard`
- On 401: show "Invalid email or password" error message
- On network error: show "Unable to connect — is the server running?"
- Loading state: disable submit button while request is in flight
- If already authenticated: redirect to `/dashboard` (don't show login form)
- Styled with Tailwind — clean, minimal, centered card layout

---

## JWT Decode (client-side)

The access token payload contains `{"sub": "<uuid>", "role": "<role>"}`.
Decode without verification (client only needs the payload — verification is the server's job):
```typescript
const payload = JSON.parse(atob(token.split('.')[1]))
// payload.sub → user id
// payload.role → role string
```
Note: `atob` is available in all modern browsers. No library needed.

---

## Done When

- [ ] Login with `admin@manifesto.local` / `admin123` redirects to `/dashboard`
- [ ] Login with wrong credentials shows error message
- [ ] Submit button disabled during request
- [ ] Already-authenticated user visiting `/login` is redirected to `/dashboard`
- [ ] No TypeScript errors
- [ ] No console errors in browser

---

## Handoffs Out

→ Adam (C21): Login flow is the primary smoke test path. Credentials: `admin@manifesto.local` / `admin123`.
