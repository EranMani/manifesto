# Commit 42 - `shipment-lifecycle-fields` - Rex

**Phase:** Demo data foundation
**Owner:** rex
**Depends on:** C41
**Estimated diff lines:** 260
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Store the shipment identity, purchase-order link, route, timing, status, and delay reason required by the demo.

## Semantic Fit Review
- **Atomic outcome:** A shipment row represents its current lifecycle state.
- **Failure boundary:** Event history remains C43.
- **Budget rationale:** One model, schema, migration, and focused model test fit four files.

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
  - backend/app/models/shipment.py
  - backend/alembic/versions/0004_shipment_lifecycle_fields.py
initial_context:
  - backend/app/models/shipment.py
  - backend/app/schemas/shipment.py
  - backend/alembic/versions/0003_purchase_order_storage.py
  - backend/tests/models/test_purchase_order_storage.py
forbidden:
  - frontend/
  - backend/app/services/
  - backend/seed.py
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/models/shipment.py` | edit | Map lifecycle fields and status constraint. |
| `backend/app/schemas/shipment.py` | edit | Expose lifecycle fields in existing shipment CRUD contracts. |
| `backend/alembic/versions/0004_shipment_lifecycle_fields.py` | add | Add lifecycle columns, constraints, and indexes. |
| `backend/tests/models/test_shipment_lifecycle.py` | add | Verify required fields, statuses, and purchase-order relationship. |

## Contract
Add unique `tracking_code`; nullable `purchase_order_id`; non-null `origin`, `destination`,
`dispatched_at`, and `expected_arrival_at`; nullable `actual_arrival_at` and
`delay_reason`; and status `pending|in_transit|delayed|delivered|partial|damaged|cancelled|returned|lost`.
Replace legacy `arrived_at` with nullable `actual_arrival_at`. Preserve `vendor_id` and
require it to match the linked purchase order at service/seeding boundaries, not by SQL constraint.

## Environment Prerequisites
- C41 purchase order storage is migrated.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/models/test_shipment_lifecycle.py -q
```

## Focused Tests
- Valid lifecycle rows persist.
- Tracking codes are unique.
- Invalid status and missing required route/timing fields fail.

## Done When
- [ ] ORM, schema, and migration agree.
- [ ] Focused tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C46 demo data ready.

## Not In This Commit
- Shipment event history or seed data.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
