# Commit 04b — `config-security-hardening` · Rex

**Phase:** 1B — Backend Core
**Assignee:** Rex (Backend)
**Depends on:** C04 (config-and-security)
**Origin:** Sage gate blocking findings from C04 — two valid, two dismissed

---

## What

Apply two targeted security hardening fixes to the modules created in C04.
No new files. No interface changes. No functional changes to happy paths.

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/core/config.py` | Add `field_validator` to reject `SECRET_KEY` values shorter than 32 characters |
| `backend/app/core/security.py` | Add `logger.warning` inside `decode_token` JWTError catch block |

---

## config.py — SECRET_KEY validator

Add a `field_validator` that rejects `SECRET_KEY` values with fewer than 32 characters.

```python
from pydantic import field_validator
```

```python
@field_validator("SECRET_KEY")
@classmethod
def secret_key_min_length(cls, v: str) -> str:
    if len(v) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters")
    return v
```

This runs at startup — weak keys cause an immediate, clear failure rather than silently signing JWTs.

---

## security.py — decode_token logging

Add structlog import and warning log in the JWTError catch:

```python
import structlog
logger = structlog.get_logger()
```

```python
except InvalidTokenError as exc:
    logger.warning("token_validation_failed", error=str(exc))
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
```

The external error message does not change — `detail` remains generic. The log is for internal forensics only.

---

## Dismissed Findings (do not implement)

| Finding | Reason dismissed |
|---|---|
| `OPENAI_API_KEY: str = ""` — "plaintext credential" | False positive. Empty string is not a secret. Standard optional-key pattern. |
| `create_access_token(data: dict)` — "unvalidated claims" | Contradicts the spec. Interface defined in C04 spec and handoffs. Internal callers only (Rex). Not a security boundary. |

---

## Done When

- [ ] `Settings(SECRET_KEY="short")` raises `ValueError` with message containing "32 characters"
- [ ] `Settings(SECRET_KEY="a" * 32)` initialises without error
- [ ] `decode_token("bad-token")` still raises HTTPException 401 (behaviour unchanged)
- [ ] `decode_token("bad-token")` emits a structlog warning line with key `token_validation_failed`

---

## Handoffs Out

None — no interface changes.
