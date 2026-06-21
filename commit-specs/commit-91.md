# Commit 91 - `add-status-reason-field` - Rex

**Phase:** Phase 3
**Owner:** rex
**Depends on:** C90
**Estimated diff lines:** 80
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Shipments carry a general-purpose `status_reason` text field that explains why a
shipment is in any exception state (damaged, lost, delayed, cancelled, returned,
partial), distinct from the existing `delay_reason` which is delay-specific.

---

## Semantic Fit Review

- **Atomic outcome:** One new nullable column on the shipments table, surfaced through
  the schema and populated in seed data. Independently testable by querying the API.
- **Failure boundary:** If the migration fails, no other commit is affected. The field
  is additive and nullable — existing code continues to work unchanged.
- **Budget rationale:** Four files, all in Rex's domain. Straightforward column addition
  with a simple migration. Well within tool and token limits.

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
  - backend/app/models/shipment.py
  - backend/app/schemas/shipment.py

initial_context:
  - commit-specs/commit-91.md
  - backend/app/models/shipment.py
  - backend/app/schemas/shipment.py
  - backend/seed.py
  - backend/alembic/versions/0006_client_shipment_items.py

forbidden:
  - frontend/
  - hooks/
  - docker-compose.yml
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/models/shipment.py` | edit | Add `status_reason: Mapped[str \| None]` column |
| `backend/alembic/versions/0007_add_status_reason.py` | add | Migration adding the `status_reason` column |
| `backend/app/schemas/shipment.py` | edit | Add `status_reason` to `ShipmentBase` and `ShipmentRead` |
| `backend/seed.py` | edit | Populate `status_reason` for all exception-status shipments |

---

## Contract

- **Model**: `Shipment.status_reason` — `Mapped[str | None]`, nullable, `String`,
  no default. Sits alongside existing `delay_reason` (not a replacement).
- **Migration**: `0007_add_status_reason` — `op.add_column('shipments',
  sa.Column('status_reason', sa.String(), nullable=True))`. Down revision:
  `0006_client_shipment_items`. Revision ID must be ≤ 32 characters.
- **Schema**: `ShipmentBase.status_reason: str | None = None`. Carried through to
  `ShipmentRead` and `ShipmentCreate`.
- **Seed**: Each `SHIPMENT_OUTCOMES` entry with a non-normal status gets a
  `status_reason` value. Use distinct phrasing from `delay_reason` — `status_reason`
  is the user-facing explanation, not the operational cause. Examples:
  - delayed: "Shipment is delayed due to weather/customs/carrier/vendor issues"
  - damaged: "Cargo found damaged during hub inspection"
  - lost: "Shipment reported lost; investigation in progress"
  - cancelled: "Order was cancelled before dispatch"
  - returned: "Delivery refused by recipient; returning to origin"
  - partial: "Only partial quantity was available for shipment"
  - delivered/in_transit/pending: `None` (no exception to explain)

---

## Environment Prerequisites

- PostgreSQL running via docker-compose (port 5433).
- Migration applied: `docker compose run --rm backend uv run alembic upgrade head`.

---

## Verification Command

```powershell
docker compose run --rm backend uv run python -c "from app.models.shipment import Shipment; print('status_reason' in [c.name for c in Shipment.__table__.columns])"
```

---

## Focused Tests

- Happy path: Import `Shipment` model and verify `status_reason` column exists.
- Schema path: Create a `ShipmentRead` instance with `status_reason` populated and
  verify serialization.
- Seed path: After re-seed, verify exception-status shipments have non-null
  `status_reason` values via the list API.

---

## Done When

- [ ] `status_reason` column exists on the `shipments` table.
- [ ] Migration upgrades and downgrades cleanly.
- [ ] Schema includes `status_reason` in request and response.
- [ ] Seed data populates `status_reason` for all exception-status shipments.
- [ ] Verification command passes.

---

## Developer Test Checkpoint

- **Next milestone:** C95 (expandable-shipment-cards) — full expandable card feature
  testable in the browser.

---

## Not In This Commit

- Shipment detail endpoint with items and events — C92.
- Redis caching — C94.
- Frontend expandable cards — C95.
- Renaming `delay_reason` to `status_reason` — deferred; would touch 9+ files
  across 3 agent domains.

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
