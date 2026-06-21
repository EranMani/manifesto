# Commit 93 - `add-redis-service` - Adam

**Phase:** Phase 3
**Owner:** adam
**Depends on:** C90
**Estimated diff lines:** 15
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Docker compose includes a Redis service so the backend can use Redis for caching
shipment detail responses.

---

## Semantic Fit Review

- **Atomic outcome:** One new service in docker-compose. Testable by running
  `docker compose up redis` and confirming connectivity.
- **Failure boundary:** If Redis fails to start, it does not affect the existing
  database or backend services. The backend's Redis client (C94) will handle
  unavailability gracefully.
- **Budget rationale:** One file in Adam's domain. Minimal diff.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 350
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

---

## Context

```yaml
primary_files:
  - docker-compose.yml

initial_context:
  - commit-specs/commit-93.md
  - docker-compose.yml

forbidden:
  - backend/app/
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `docker-compose.yml` | edit | Add Redis service, volume, and backend dependency |

---

## Contract

- **Service**: `redis` using `redis:7-alpine` image.
- **Port mapping**: `6379:6379`.
- **Volume**: `redis_data:/data` for persistence.
- **Backend depends_on**: Add `redis` to backend's `depends_on` block (no health check
  needed — Redis starts in milliseconds).
- **Volume declaration**: Add `redis_data` to the top-level `volumes` block.

---

## Environment Prerequisites

- Docker and docker-compose installed.

---

## Verification Command

```powershell
docker compose config --services
```

---

## Focused Tests

- Happy path: `docker compose config --services` lists `redis` alongside `db`,
  `ollama`, and `backend`.
- Volume path: `docker compose config` output includes `redis_data` volume.
- Dependency path: Backend service config includes `redis` in its dependencies.

---

## Done When

- [ ] `docker compose config --services` includes `redis`.
- [ ] Redis service uses `redis:7-alpine` image.
- [ ] Backend declares `depends_on` for redis.
- [ ] `redis_data` volume is declared.

---

## Developer Test Checkpoint

- **Next milestone:** C95 (expandable-shipment-cards) — full expandable card feature
  testable in the browser.

---

## Not In This Commit

- Redis client utility in the backend — C94.
- Cache logic in shipment routes — C94.
- REDIS_URL configuration setting — C94.

---

## Return Contract

```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```
