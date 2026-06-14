# Commit 47 - `shipment-identifier-evidence` - Nova

**Phase:** Logistics evidence
**Owner:** nova
**Depends on:** C46
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Resolve one shipment by normalized tracking code and return typed authoritative evidence.

## Semantic Fit Review
- **Atomic outcome:** Identifier lookup has one deterministic result contract.
- **Failure boundary:** Relationship expansion remains C48.
- **Budget rationale:** One service and test file fit the envelope.

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
  - backend/app/models/shipment.py
  - backend/app/core/database.py
  - backend/tests/services/test_rag_policy.py
forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/models/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add typed shipment identifier lookup. |
| `backend/tests/services/test_rag_logistics.py` | add | Verify normalization, result shape, and misses. |

## Contract
Add `ShipmentEvidence` and `ShipmentNotFoundError`. `lookup_shipment(db, tracking_code)`
trims and uppercases the identifier, rejects blank input, executes one parameterized
SELECT, and returns id, tracking code, status, route, lifecycle timestamps, and delay reason.

## Environment Prerequisites
- C45 shipment scenarios are seeded.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k identifier -q
```

## Focused Tests
- Normalized known identifiers resolve.
- Unknown and blank identifiers fail safely.
- No write statement is executed.

## Done When
- [ ] Lookup contract and tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C50 logistics evidence ready.

## Not In This Commit
- Orders, products, timelines, graph payloads, or answer generation.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
