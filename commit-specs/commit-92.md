# Commit 92 - `shipment-detail-endpoint` - Rex

**Phase:** Phase 3
**Owner:** rex
**Depends on:** C91
**Estimated diff lines:** 120
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

A new `GET /api/v1/shipments/{id}/detail` endpoint returns the full shipment record
with nested product items (including product name and unit) and the chronological
event timeline, enabling the frontend to fetch rich detail on demand.

---

## Semantic Fit Review

- **Atomic outcome:** One new endpoint returning an enriched response shape. Testable
  independently by calling the endpoint and verifying the response structure.
- **Failure boundary:** If this endpoint fails, the existing `GET /{id}` and list
  endpoints continue to work. No existing behavior is changed.
- **Budget rationale:** Two files in Rex's domain. The endpoint is a straightforward
  join query with new response schemas.

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
  - backend/app/api/v1/shipments.py
  - backend/app/schemas/shipment.py

initial_context:
  - commit-specs/commit-92.md
  - backend/app/api/v1/shipments.py
  - backend/app/schemas/shipment.py
  - backend/app/models/shipment.py
  - backend/app/models/shipment_item.py
  - backend/app/models/shipment_event.py

forbidden:
  - frontend/
  - hooks/
  - docker-compose.yml
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/schemas/shipment.py` | edit | Add `ShipmentItemDetail`, `ShipmentEventDetail`, `ShipmentDetailRead` |
| `backend/app/api/v1/shipments.py` | edit | Add `GET /{shipment_id}/detail` endpoint |

---

## Contract

### New schemas

- **`ShipmentItemDetail`** (BaseModel):
  - `product_id: str`
  - `product_name: str`
  - `product_unit: str | None`
  - `quantity: int`

- **`ShipmentEventDetail`** (BaseModel):
  - `event_type: str`
  - `occurred_at: datetime.datetime`
  - `location: str`
  - `details: str | None`

- **`ShipmentDetailRead`** (ShipmentRead):
  - `items: list[ShipmentItemDetail]`
  - `events: list[ShipmentEventDetail]`

### Endpoint

- **Route**: `GET /api/v1/shipments/{shipment_id}/detail`
- **Auth**: `require_role("admin", "manager")`
- **Success (200)**: Returns `ShipmentDetailRead` with:
  - All fields from `ShipmentRead` (including `status_reason` from C91)
  - `items`: joined from `shipment_items` → `products` (name, unit)
  - `events`: from `shipment_events`, ordered by `occurred_at ASC`
- **404**: `"Shipment not found"`
- **Query**: Single query with joined loads or two follow-up queries. No N+1.

---

## Environment Prerequisites

- PostgreSQL running via docker-compose.
- Seed data loaded (provides shipments with items and events).

---

## Verification Command

```powershell
docker compose run --rm backend uv run python -c "from app.schemas.shipment import ShipmentDetailRead; print(ShipmentDetailRead.model_fields.keys())"
```

---

## Focused Tests

- Happy path: Call `GET /shipments/{id}/detail` for a seeded shipment with items and
  events; verify response contains `items` array with product names and `events` array
  sorted chronologically.
- Empty items: Call detail for a shipment with no items; verify `items` is an empty list.
- 404 path: Call detail with a non-existent ID; verify 404 response.

---

## Done When

- [ ] `GET /api/v1/shipments/{id}/detail` returns items with product names and events.
- [ ] Events are sorted by `occurred_at` ascending.
- [ ] No N+1 queries.
- [ ] Verification command passes.

---

## Developer Test Checkpoint

- **Next milestone:** C95 (expandable-shipment-cards) — full expandable card feature
  testable in the browser.

---

## Not In This Commit

- Redis caching of the detail response — C94.
- Frontend expandable cards consuming this endpoint — C95.
- Cache invalidation on shipment mutations — C94.

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
