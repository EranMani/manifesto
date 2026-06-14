# Commit 48 - `procurement-relationship-evidence` - Nova

**Phase:** Logistics evidence
**Owner:** nova
**Depends on:** C47
**Estimated diff lines:** 240
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Expand shipment evidence to its buyer, purchase order, vendor, and products.

## Semantic Fit Review
- **Atomic outcome:** One bounded relational path returns authoritative related entities.
- **Failure boundary:** Timeline evidence remains C49.
- **Budget rationale:** Existing logistics service and tests contain the bounded expansion.

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
  - backend/app/services/rag_logistics.py
  - backend/tests/services/test_rag_logistics.py
initial_context:
  - backend/app/services/rag_logistics.py
  - backend/tests/services/test_rag_logistics.py
  - backend/app/models/purchase_order.py
  - backend/app/models/product.py
  - backend/app/models/vendor.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add bounded procurement relationship expansion. |
| `backend/tests/services/test_rag_logistics.py` | edit | Verify exact related entities and deterministic ordering. |

## Contract
Add `ProcurementEvidence` containing the shipment, optional purchase order, internal
buyer, vendor, and products sorted by product name then id. Use allowlisted ORM/select
joins only and return no password, email, or internal notes fields.

## Environment Prerequisites
- C47 identifier lookup is frozen.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k relationships -q
```

## Focused Tests
- Golden shipment returns its exact buyer/order/vendor/products.
- Missing optional order is represented explicitly.
- Sensitive user fields are absent.

## Done When
- [ ] Relationship evidence is deterministic.
- [ ] Focused tests pass.

## Developer Test Checkpoint
**Next milestone:** C50 logistics evidence ready.

## Not In This Commit
- Timeline or graph serialization.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
