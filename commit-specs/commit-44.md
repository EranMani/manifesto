# Commit 44 - `procurement-foundation-seed` - Rex

**Phase:** Demo data foundation
**Owner:** rex
**Depends on:** C43
**Estimated diff lines:** 230
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Idempotently seed stable demo users, vendors, categories, and purchase orders.

## Semantic Fit Review
- **Atomic outcome:** Foundational procurement entities have stable identifiers.
- **Failure boundary:** Shipment scenarios remain C45.
- **Budget rationale:** Seed implementation and focused test are isolated to two files.

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
  - backend/app/models/purchase_order.py
  - backend/app/models/vendor.py
  - backend/app/models/user.py
  - backend/app/models/category.py
forbidden:
  - frontend/
  - backend/app/services/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/seed.py` | edit | Add stable procurement foundation data. |
| `backend/tests/test_seed.py` | add | Verify counts, identifiers, relationships, and idempotency. |

## Contract
Seed the existing admin plus two managers as buyers, eight vendors, six categories, and
twenty purchase orders using deterministic emails/order numbers and fixed 2026 timestamps.
Running the seed repeatedly must update nothing unexpectedly and create no duplicates.

## Environment Prerequisites
- C41-C43 migrations are at head.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/test_seed.py -k procurement_foundation -q
```

## Focused Tests
- Stable counts and keys are created.
- Orders reference seeded buyers and vendors.
- A second run is idempotent.

## Done When
- [ ] Foundation seed is deterministic.
- [ ] Focused tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C46 demo data ready.

## Not In This Commit
- Shipments, products, events, or policy documents.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
