# Commit 10 — `auth-route` · Rex

**Phase:** 1C — Auth & User Management
**Assignee:** Rex (Backend)
**Depends on:** C09 (auth-dependencies)

**Viktor + Sage wave runs on this commit (C10 is the 10th commit; Sage triggered by auth route).**

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
