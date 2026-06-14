# Commit 49 - `shipment-timeline-evidence` - Nova

**Phase:** Logistics evidence
**Owner:** nova
**Depends on:** C48
**Estimated diff lines:** 210
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Attach a deterministic event timeline and delay explanation to procurement evidence.

## Semantic Fit Review
- **Atomic outcome:** Current shipment state is supported by chronological events.
- **Failure boundary:** Graph projection remains C50.
- **Budget rationale:** One service/test pair extends the existing evidence contract.

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
  - backend/app/models/shipment_event.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add ordered event and delay evidence. |
| `backend/tests/services/test_rag_logistics.py` | edit | Verify chronology and exception evidence. |

## Contract
Return events ordered by `(occurred_at, id)`. For delayed, damaged, partial, cancelled,
returned, or lost shipments, expose the current reason plus the latest supporting
exception event. Do not infer a reason absent from stored data.

## Environment Prerequisites
- C48 procurement evidence is available.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k timeline -q
```

## Focused Tests
- Timeline order is stable.
- Exception reason maps to stored evidence.
- Missing reasons remain unknown rather than invented.

## Done When
- [ ] Timeline evidence passes focused tests.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C50 logistics evidence ready.

## Not In This Commit
- Graph nodes/edges or LLM generation.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
