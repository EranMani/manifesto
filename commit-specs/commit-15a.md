# Commit 15a — `fix-admin-update` · Rex

**Phase:** 1E — Viktor Fix Wave
**Assignee:** Rex (Backend)
**Depends on:** C15 (stub-routes)
**Triggered by:** Viktor batch wave C11–C15, Finding 1 (BLOCK)

**No gate wave on this commit. Viktor covered C11–C15 at C15. Next batch wave: C20.**
**Sage conditional: yes — touches user data mutation and password hashing.**

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/api/v1/admin.py    # route to fix
  - backend/app/schemas/user.py    # schema to extend

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/api/v1/auth.py
  - backend/app/api/v1/vendors.py
  - backend/app/api/v1/shipments.py
  - backend/app/api/v1/products.py

estimated_reads: 2
estimated_edits: 2   # admin.py (fix), user.py (extend UserUpdate)
fits_single_agent: true
```

---

## What

Fix two bugs in `admin.py` `update_user` found by Viktor batch wave:

1. **Silent field discard** — `UserUpdate` only has `role` and `is_active`. A PUT with `name`, `email`, or `password` silently discards those fields. Extend `UserUpdate` and handle all five mutable fields.
2. **Self-demotion** — No guard prevents an admin from removing their own admin role. Add a 403 check.

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/schemas/user.py` | Add `name: str \| None`, `email: str \| None`, `password: str \| None` to `UserUpdate` |
| `backend/app/api/v1/admin.py` | Handle new fields in `update_user`; add self-demotion guard; replace `_` with `current_user` |

---

## Exact Changes

### `backend/app/schemas/user.py` — extend UserUpdate

```python
class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    role: Literal["admin", "manager", "employee"] | None = None
    is_active: bool | None = None
```

### `backend/app/api/v1/admin.py` — fix update_user

```python
@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> UserRead:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.role is not None and str(current_user.id) == user_id and payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot demote yourself")
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return user
```

Note: `hash_password` is already imported at the top of `admin.py`.

---

## Done When

- [ ] `UserUpdate` has 5 optional fields: `name`, `email`, `password`, `role`, `is_active`
- [ ] `update_user` handles all five fields
- [ ] PUT with `{"role": "employee"}` on own user_id returns 403
- [ ] PUT with `{"name": "New Name"}` updates the name in the DB
