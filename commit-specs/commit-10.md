# Commit 10 — `auth-route` · Rex

**Phase:** 1C — Auth & User Management
**Assignee:** Rex (Backend)
**Depends on:** C09 (auth-dependencies)

**Viktor + Sage wave runs on this commit (C10 is the 10th commit; Sage triggered by auth route).**

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/main.py            # to register the router
  - backend/app/core/database.py   # need get_db
  - backend/app/core/security.py   # need verify_password, create_access_token
  - backend/app/models/user.py     # need User model

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/dependencies.py    # already done in C09, read-only if needed

estimated_reads: 4
estimated_edits: 3   # auth.py (new), schemas/auth.py (new), main.py (update)
fits_single_agent: true
```

---

## What

Implement the login route. One endpoint: `POST /auth/login`.
Returns a JWT access token on valid credentials.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/auth.py` | new | POST /auth/login route |
| `backend/app/schemas/auth.py` | new | LoginRequest, TokenResponse Pydantic schemas |

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/main.py` | Register auth router under `/auth` |

---

## Schemas

```python
class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

---

## Route Logic

```
POST /auth/login
  → fetch User by email from DB
  → if not found or not active → 401
  → verify_password(request.password, user.password_hash)
  → if fails → 401
  → create_access_token({"sub": str(user.id), "role": user.role})
  → return TokenResponse
```

Error messages must not reveal whether email or password was wrong — use generic "Invalid credentials".

---

## Done When

- [ ] `POST /auth/login` with seed credentials returns `{access_token: "...", token_type: "bearer"}`
- [ ] `POST /auth/login` with wrong password returns 401
- [ ] `POST /auth/login` with unknown email returns 401
- [ ] Error body says "Invalid credentials" — does not reveal which field failed
- [ ] Route appears in `GET /docs`

---

## Handoffs Out

→ Aria (C17): Token format is `{access_token: string, token_type: "bearer"}`. Store `access_token` in Zustand, attach as `Authorization: Bearer <token>` header.

---

## Security Note (Sage C09 Finding #1 — verify at C10)

Sage flagged during the C09 gate that the `get_current_user` dependency trusts the JWT `sub` claim as the user ID. This is safe **only if** the login route issues tokens with `sub` hardcoded to the authenticated user's own ID after password verification. The C10 spec already prescribes exactly this:

```python
create_access_token({"sub": str(user.id), "role": user.role})
```

Rex: confirm this line is the only call to `create_access_token` in the login route, and that it is placed **after** `verify_password` succeeds. Sage will re-review this commit (C10 triggers Viktor + Sage wave).
