# Commit 45 - `shipment-scenario-seed` - Rex

**Phase:** Demo data foundation
**Owner:** rex
**Depends on:** C44
**Estimated diff lines:** 320
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Idempotently seed 50 curated shipment scenarios with products and event timelines.

## Semantic Fit Review
- **Atomic outcome:** The logistics demo has representative operational outcomes.
- **Failure boundary:** Policy content remains C46.
- **Budget rationale:** Scenario definitions and tests stay in the existing seed/test pair.

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
  - backend/seed.py
  - backend/tests/test_seed.py
initial_context:
  - backend/seed.py
  - backend/tests/test_seed.py
  - backend/app/models/shipment.py
  - backend/app/models/shipment_event.py
  - backend/app/models/product.py
forbidden:
  - frontend/
  - backend/app/services/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/seed.py` | edit | Add curated shipment, product, and event scenarios. |
| `backend/tests/test_seed.py` | edit | Verify scenario coverage and idempotency. |

## Contract
Seed exactly 50 shipments with stable `SHP-1001` through `SHP-1050` tracking codes,
one to four products each, and chronological events. Cover delivered, in-transit,
pending, weather delay, customs hold, carrier delay, vendor delay, partial, damaged,
cancelled, returned, and lost outcomes. At least one golden scenario per exceptional
outcome must have an explicit delay reason and evidence event.

## Environment Prerequisites
- C44 foundation data exists.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/test_seed.py -k shipment_scenarios -q
```

## Focused Tests
- Exactly 50 stable shipments are created.
- Every required outcome is represented.
- Products and events link correctly and a rerun is idempotent.

## Done When
- [ ] Scenario coverage is complete.
- [ ] Focused tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C46 demo data ready.

## Not In This Commit
- Policy data or assistant retrieval.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
