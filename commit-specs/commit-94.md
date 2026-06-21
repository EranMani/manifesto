# Commit 94 - `redis-shipment-detail-cache` - Rex

**Phase:** Phase 3
**Owner:** rex
**Depends on:** C92, C93
**Estimated diff lines:** 150
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

The shipment detail endpoint caches its response in Redis with a 5-minute TTL so
repeated expansions of the same shipment card return instantly. The cache is
invalidated when a shipment is created or deleted.

---

## Semantic Fit Review

- **Atomic outcome:** One caching layer wrapping the detail endpoint. Testable by
  verifying cache hits (faster response, Redis key present) and invalidation
  (key removed on mutation).
- **Failure boundary:** If Redis is unavailable, the endpoint degrades gracefully
  and serves directly from the database. No user-facing error.
- **Budget rationale:** Four files in Rex's domain. The Redis client is a small
  utility; the caching integration is mechanical.

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
  - backend/app/core/redis.py
  - backend/app/api/v1/shipments.py

initial_context:
  - commit-specs/commit-94.md
  - backend/app/api/v1/shipments.py
  - backend/app/core/config.py
  - backend/app/schemas/shipment.py
  - docker-compose.yml

forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/core/config.py` | edit | Add `REDIS_URL` setting with default |
| `backend/app/core/redis.py` | add | Async Redis client utility (get, set, delete) |
| `backend/app/api/v1/shipments.py` | edit | Cache detail response, invalidate on create/delete |
| `backend/pyproject.toml` | edit | Add `redis` dependency |

---

## Contract

### Config

- `Settings.REDIS_URL: str = "redis://redis:6379/0"` — matches the docker-compose
  service name. No validator needed (Redis client handles connection errors).

### Redis client (`backend/app/core/redis.py`)

- `get_redis() -> redis.asyncio.Redis` — returns a shared async Redis client,
  created lazily on first call.
- `async cache_get(key: str) -> str | None` — get a cached value. Returns `None`
  on cache miss or Redis error.
- `async cache_set(key: str, value: str, ttl: int = 300) -> None` — set a value
  with TTL. Silently ignores Redis errors.
- `async cache_delete(key: str) -> None` — delete a key. Silently ignores errors.
- All functions catch `redis.RedisError` and `ConnectionError` — Redis down means
  cache miss, not application error.

### Caching in shipments.py

- **Detail endpoint** (`GET /{id}/detail`):
  - Cache key: `shipment:detail:{shipment_id}`
  - On request: check cache first. If hit, return cached JSON directly.
  - On miss: query DB, serialize response, store in cache with 300s TTL, return.
- **Create endpoint** (`POST /`): no cache to invalidate (new shipment).
- **Delete endpoint** (`DELETE /{id}`): delete `shipment:detail:{id}` from cache.

### Dependency

- `redis>=5.0` added to `backend/pyproject.toml` dependencies.

---

## Environment Prerequisites

- Redis service running via docker-compose (C93).
- PostgreSQL running via docker-compose.
- Seed data loaded.

---

## Verification Command

```powershell
docker compose run --rm backend uv run python -c "from app.core.redis import get_redis; print('Redis client loaded')"
```

---

## Focused Tests

- Happy path: Call detail endpoint twice for the same shipment; verify second call
  uses cached response (check Redis key exists).
- Cache miss: Call detail for a shipment with no cache entry; verify DB query runs
  and cache is populated.
- Invalidation: Delete a shipment; verify its cache key is removed.
- Redis down: With Redis unavailable, detail endpoint still returns correct data
  from the database (graceful degradation).

---

## Done When

- [ ] `REDIS_URL` setting exists in config with docker-compose default.
- [ ] Redis client utility provides get/set/delete with error handling.
- [ ] Detail endpoint caches responses with 5-minute TTL.
- [ ] Delete endpoint invalidates the cache.
- [ ] Endpoint works correctly when Redis is unavailable.
- [ ] `redis` dependency added to pyproject.toml.

---

## Developer Test Checkpoint

- **Next milestone:** C95 (expandable-shipment-cards) — full expandable card feature
  testable in the browser.

---

## Not In This Commit

- Frontend expandable cards consuming the cached endpoint — C95.
- Cache invalidation on shipment update (no update endpoint exists yet).

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
