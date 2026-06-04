# Commit 04 — `config-and-security` · Rex

**Phase:** 1B — Backend Core
**Assignee:** Rex (Backend)
**Depends on:** C02 (python-skeleton)

---

## What

Implement configuration management and security utilities. No routes, no DB, no models.
These are pure utility modules — the foundation every other backend module imports from.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/core/config.py` | new | pydantic-settings Settings class, all env vars |
| `backend/app/core/security.py` | new | hash_password, verify_password, create_access_token, decode_token |

---

## core/config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## core/security.py

Implement:
- `hash_password(plain: str) -> str` — bcrypt via passlib
- `verify_password(plain: str, hashed: str) -> bool`
- `create_access_token(data: dict) -> str` — JWT, expiry from settings
- `decode_token(token: str) -> dict` — raises HTTPException 401 on invalid/expired

---

## Done When

- [ ] `from app.core.config import settings` imports without error
- [ ] `from app.core.security import hash_password, verify_password` imports without error
- [ ] `hash_password("test")` returns a bcrypt hash string
- [ ] `verify_password("test", hash_password("test"))` returns True
- [ ] `decode_token(create_access_token({"sub": "test"}))` returns `{"sub": "test"}`
- [ ] `decode_token("bad-token")` raises HTTPException with status 401

---

## Handoffs Out

→ Rex (C08): `create_access_token` accepts a `data: dict` — caller must pass `{"sub": str(user.id), "role": user.role}`.
→ Rex (C09): `decode_token` raises HTTPException 401 — `get_current_user` dependency catches this naturally.
