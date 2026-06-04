# Commit 08 — `seed-script` · Rex

**Phase:** 1B — Backend Core
**Assignee:** Rex (Backend)
**Depends on:** C07 (alembic-migration) — schema must exist before seed runs

---

## What

Create the seed script that inserts a default admin user for local development.
Idempotent — running it twice must not create duplicate users or raise errors.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/seed.py` | new | Standalone script, run via `python seed.py` from backend/ |

---

## Seed User

```
email:    admin@manifesto.local
password: admin123
role:     admin
name:     Admin
```

---

## seed.py Requirements

- Uses `asyncio.run()` — async script
- Imports `AsyncSessionLocal` from `app.core.database`
- Checks if `admin@manifesto.local` already exists before inserting (idempotent)
- Uses `hash_password` from `app.core.security`
- Prints confirmation: `"Seed complete — admin@manifesto.local created"` or `"Seed skipped — user already exists"`
- Must be runnable with: `cd backend && python seed.py`

---

## Done When

- [ ] `python seed.py` runs without errors against live Postgres
- [ ] Admin user exists in `users` table after running
- [ ] Running `python seed.py` a second time prints "skipped" and makes no changes
- [ ] `password_hash` in DB is a valid bcrypt hash (not plaintext)

---

## Handoffs Out

→ Rex (C09): Admin user exists with `role='admin'`. `get_current_user` dependency can be tested with real credentials from this point.
→ Aria (C20): Login credentials for frontend testing: `admin@manifesto.local` / `admin123`.
