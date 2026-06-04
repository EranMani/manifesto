# Commit 17 — `auth-store-and-client` · Aria

**Phase:** 1F — Frontend Core
**Assignee:** Aria (Frontend)
**Depends on:** C10 (auth-route) — token format must be known; C03 (frontend-scaffold) — src/ exists

---

## What

Implement the Zustand auth store, Axios client with JWT interceptor, and login API call.
No UI yet — pure state and API layer.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `frontend/src/store/auth.ts` | new | Zustand slice: token, user (id, role, name), login, logout |
| `frontend/src/api/client.ts` | new | Axios instance, base URL, JWT interceptor, 401 handler |
| `frontend/src/api/auth.ts` | new | login(email, password) → TokenResponse |

---

## store/auth.ts

```typescript
interface AuthState {
  token: string | null
  user: { id: string; role: string; name: string } | null
  login: (token: string, user: AuthState['user']) => void
  logout: () => void
}
```

Store token in memory (Zustand state) only — no localStorage.
Decode the JWT payload client-side to extract `sub` (user id) and `role`.

---

## api/client.ts

```typescript
// Axios instance with:
// - baseURL: import.meta.env.VITE_API_BASE_URL || ''
// - request interceptor: attach Authorization: Bearer <token> from auth store
// - response interceptor: on 401 → call logout() → redirect to /login
```

---

## api/auth.ts

```typescript
export async function loginApi(email: string, password: string): Promise<TokenResponse>
// POST /auth/login
// Returns { access_token, token_type }
```

---

## Done When

- [ ] `useAuthStore()` returns `{ token, user, login, logout }`
- [ ] `loginApi` function exists and is typed
- [ ] Axios interceptor attaches token header when token is set
- [ ] Axios interceptor calls logout and redirects on 401
- [ ] No browser console errors on `npm run dev`

---

## Handoffs Out

→ Aria (C18): `useAuthStore` is the auth source of truth for `ProtectedRoute`. Check `user.role` from the store.
→ Aria (C20): `loginApi` is the function Login page calls. On success, call `store.login(token, decodedUser)` then navigate to `/dashboard`.
