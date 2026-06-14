# Commit 43 - `shipment-event-storage` - Rex

**Phase:** Demo data foundation
**Owner:** rex
**Depends on:** C42
**Estimated diff lines:** 250
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Persist an ordered event timeline for each shipment.

## Semantic Fit Review
- **Atomic outcome:** Shipment history is represented independently from current status.
- **Failure boundary:** Scenario population remains C45.
- **Budget rationale:** One model, export, migration, and focused test fit four files.

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

## Context
```yaml
primary_files:
  - backend/app/models/shipment_event.py
  - backend/alembic/versions/0005_shipment_event_storage.py
initial_context:
  - backend/app/models/shipment.py
  - backend/app/models/__init__.py
  - backend/alembic/versions/0004_shipment_lifecycle_fields.py
  - backend/tests/models/test_shipment_lifecycle.py
forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/services/
  - backend/seed.py
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/models/shipment_event.py` | add | Map timestamped shipment events. |
| `backend/app/models/__init__.py` | edit | Export ShipmentEvent. |
| `backend/alembic/versions/0005_shipment_event_storage.py` | add | Create event table and timeline index. |
| `backend/tests/models/test_shipment_event_storage.py` | add | Verify event types, cascade, and ordering. |

## Contract
Create `shipment_events` with UUID id, non-null shipment FK with cascade delete,
non-null `event_type`, `occurred_at`, and `location`, nullable `details`, and `created_at`.
Allow event types `ordered|dispatched|departed|arrived_hub|customs_hold|customs_released|delay_reported|damaged|partial_delivery|delivered|cancelled|returned|lost`.
Index `(shipment_id, occurred_at, id)` for deterministic chronology.

## Environment Prerequisites
- C42 shipment lifecycle schema is migrated.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/models/test_shipment_event_storage.py -q
```

## Focused Tests
- Events sort deterministically.
- Invalid types fail.
- Deleting a shipment deletes its events.

## Done When
- [ ] Storage contract is implemented.
- [ ] Focused tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C46 demo data ready.

## Not In This Commit
- Event APIs, retrieval, or seed scenarios.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
