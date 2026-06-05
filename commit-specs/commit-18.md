# Commit 18 — `protected-route` · Aria

**Phase:** 1F — Frontend Core
**Assignee:** Aria (Frontend)
**Depends on:** C17 (auth-store-and-client)

---

## context

```
tier0:
  - .claude/agents/aria.md (Current State header only — first 50 lines)

tier1:
  - frontend/src/store/auth.ts    # need useAuthStore shape (from C17)
  - frontend/src/App.tsx          # existing file to update

tier2: []

forbidden:
  - backend/
  - frontend/src/pages/           # stub pages don't exist yet — use inline stubs
  - frontend/src/api/             # API layer done in C17, do not touch

estimated_reads: 2
estimated_edits: 2   # ProtectedRoute.tsx (new), App.tsx (update)
fits_single_agent: true
```

---

## What

Implement role-based route guard and wire up React Router with all routes defined.
No real page content yet — pages are imported from placeholder files that don't exist yet.
Use lazy imports or stub components inline to avoid import errors.

---

## Files to Create/Modify

| File | Type | Description |
|---|---|---|
| `frontend/src/components/ProtectedRoute.tsx` | new | Role-based route guard component |
| `frontend/src/App.tsx` | update | Full router setup with all routes |

---

## ProtectedRoute.tsx

```typescript
// Props: allowedRoles: string[]
// If no token → redirect to /login
// If token but role not in allowedRoles → redirect to /unauthorized (or /login)
// If authorized → render <Outlet />
```

---

## App.tsx Route Table

```
/login                          — public
/dashboard                      — manager, admin
/vendors                        — manager, admin
/vendors/:id                    — manager, admin
/chat/policy                    — manager, admin, employee
/chat/logistics                 — manager, admin
/admin                          — admin only
/                               — redirect to /dashboard if authenticated, else /login
```

All protected routes wrapped in `<ProtectedRoute allowedRoles={[...]}>`.

---

## Done When

- [ ] Navigating to `/dashboard` without a token redirects to `/login`
- [ ] Navigating to `/admin` with a manager role redirects (not 403 — frontend handles this)
- [ ] Router renders without errors (placeholder pages can be `<div>Coming soon</div>` inline)
- [ ] All route paths defined in App.tsx match the spec table above
