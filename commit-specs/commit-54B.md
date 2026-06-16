# Commit 54B - `rag-logistics-vendor-lookup-fix` - Rex

**Phase:** Assistant backend
**Owner:** rex
**Depends on:** C54
**Estimated diff lines:** 30
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Fix two latent defects in rag_logistics.py surfaced by Viktor's C46-C55 gate wave: defensive vendor lookup and explicit latest-exception-event selection.

## Semantic Fit Review
- **Atomic outcome:** Vendor lookup crash path eliminated; delay evidence selection made deterministic.
- **Failure boundary:** No API surface change; internal service correctness only.
- **Budget rationale:** Two targeted edits in one file plus focused regression tests.

## Execution Budget
```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 3
  max_context_files: 4
  max_context_chars: 8000
  max_estimated_diff_lines: 60
  max_agent_invocations: 1
  max_tool_calls: 12
  max_expansions: 1
  max_implementor_tokens: 20000
```

## Context
```yaml
primary_files:
  - backend/app/services/rag_logistics.py
  - backend/tests/services/test_rag_logistics.py
initial_context:
  - backend/app/models/shipment.py
  - backend/app/models/vendor.py
forbidden:
  - frontend/
  - backend/app/api/v1/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Replace scalar_one() with scalar_one_or_none() + ShipmentNotFoundError for vendor; replace event loop with explicit max(). |
| `backend/tests/services/test_rag_logistics.py` | edit | Add focused regression tests for vendor-missing path and delay-event selection. |

## Contract
`lookup_procurement()` raises `ShipmentNotFoundError` (not `NoResultFound`) when vendor row is absent. `_delay_evidence()` selects the latest exception event by `(occurred_at, id)` via `max()` with an explicit key, not by loop reassignment.

## Environment Prerequisites
- C54 completed.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -q
```

## Focused Tests
- `lookup_procurement()` raises `ShipmentNotFoundError` when vendor_id references a missing vendor.
- `_delay_evidence()` returns the latest exception event when multiple matching events exist.

## Done When
- [ ] Both fixes applied.
- [ ] Focused tests pass.
- [ ] Scope within budget.

## Developer Test Checkpoint
**Next milestone:** C55 (assistant-role-authorization) — do not start until C54B is committed.

## Not In This Commit
- Any other rag_logistics.py changes.
- Graph path clarity (MEDIUM finding — advisory only, deferred).

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 10, return `SPLIT_REQUIRED`.
