# QA: pgAdmin Connection to Docker PostgreSQL

## Issue 1 — Password authentication failed

**Symptom:** pgAdmin returned `FATAL: password authentication failed for user "manifesto"` when connecting to `localhost:5432`.

**Root cause:** A standalone PostgreSQL instance was installed on Windows and listening on port 5432. pgAdmin was connecting to that local Postgres — not the Docker container — and the local instance had no "manifesto" user.

**Fix:** Changed the Docker port mapping in `docker-compose.yml` from `"5432:5432"` to `"5433:5432"` to avoid the conflict, then restarted the container:

```
docker compose down
docker compose up db -d
```

pgAdmin was then pointed to port 5433.

**Why it works:** The local Postgres keeps port 5432, and Docker exposes its Postgres on 5433. No collision, no ambiguity about which server pgAdmin reaches.

---

## Issue 2 — No "public" schema visible in pgAdmin

**Symptom:** After connecting successfully, the `public` schema did not appear under the `manifesto` database — no tables were listed.

**Root cause:** The database existed (created by the `POSTGRES_DB` env var on container init) but no tables had been created. Alembic migrations had not been run.

**Fix:** Ran migrations inside the backend container:

```
docker compose exec backend uv run alembic upgrade head
```

**Why it works:** Alembic applies all migration scripts (`0001` through `0005`) which issue the `CREATE TABLE` statements. After running, the public schema is populated with all project tables.

---

## pgAdmin Connection Settings

| Field    | Value      |
|----------|------------|
| Host     | localhost  |
| Port     | 5433       |
| Database | manifesto  |
| Username | manifesto  |
| Password | manifesto  |
