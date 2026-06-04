# Commit 09 — `auth-dependencies` · Rex

**Phase:** 1C — Auth & User Management
**Assignee:** Rex (Backend)
**Depends on:** C08 (seed-script) — real user in DB for manual testing

---

## What

Implement FastAPI dependency functions for authentication and authorization.
No routes yet — these are reusable dependencies that all route files will import.

---

## Files to Modify/Create

| File | Type | Description |
|---|---|---|
| `backend/app/dependencies.py` | update | Implement get_current_user and require_role |

---

## dependencies.py

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # decode token → get user_id → fetch from DB → check is_active
    # raises 401 if invalid token
    # raises 401 if user not found or inactive

def require_role(*roles: str):
    # returns a dependency that calls get_current_user
    # raises 403 if user.role not in roles
```

---

## Done When

- [ ] `from app.dependencies import get_current_user, require_role` imports without error
- [ ] `get_current_user` with a valid token returns the User ORM object
- [ ] `get_current_user` with an invalid token raises HTTPException 401
- [ ] `require_role("admin")` dependency raises 403 when called with a manager token
- [ ] `require_role("admin", "manager")` passes for both roles

---

## Handoffs Out

→ Rex (C10): `get_current_user` returns `User` ORM model. Auth route uses `verify_password` directly — does not use this dependency (login is unauthenticated by definition).
→ Rex (C11): `require_role("admin")` is the guard for all admin routes.
→ Rex (C12–C14): `require_role("admin", "manager")` guards all inventory routes.
