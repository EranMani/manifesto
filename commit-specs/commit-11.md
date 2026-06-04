# Commit 11 — `admin-routes` · Rex

**Phase:** 1C — Auth & User Management
**Assignee:** Rex (Backend)
**Depends on:** C10 (auth-route)

---

## What

Implement user management routes for the admin panel. All routes require `admin` role.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/admin.py` | new | GET/POST/PUT /api/v1/admin/users |
| `backend/app/schemas/user.py` | new | UserRead, UserCreate, UserUpdate schemas |

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/main.py` | Register admin router under `/api/v1/admin` |

---

## Routes

```
GET  /api/v1/admin/users          — list all users (paginate later; return all for now)
POST /api/v1/admin/users          — create user (name, email, password, role)
PUT  /api/v1/admin/users/{id}     — update role or is_active status
```

All routes: `Depends(require_role("admin"))`.

---

## Schemas

```python
class UserRead(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Literal["admin", "manager", "employee"]

class UserUpdate(BaseModel):
    role: Literal["admin", "manager", "employee"] | None = None
    is_active: bool | None = None
```

---

## Done When

- [ ] `GET /api/v1/admin/users` with admin token returns list containing seed user
- [ ] `GET /api/v1/admin/users` with manager token returns 403
- [ ] `GET /api/v1/admin/users` with no token returns 401
- [ ] `POST /api/v1/admin/users` creates a user (verify in DB)
- [ ] `PUT /api/v1/admin/users/{id}` updates role or is_active
- [ ] All routes appear in `/docs`

---

## Handoffs Out

→ Aria (C19): Admin page at `/admin` renders a user list. Backend returns `UserRead` schema — fields: id, name, email, role, is_active, created_at.
