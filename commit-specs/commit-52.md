# Commit 52 - `assistant-intent-routing` - Nova

**Phase:** Assistant backend
**Owner:** nova
**Depends on:** C51
**Estimated diff lines:** 190
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Classify a question as logistics, policy, or mixed with normalized extracted identifiers.

## Semantic Fit Review
- **Atomic outcome:** One deterministic routing decision selects evidence sources.
- **Failure boundary:** Answer generation remains C53-C54.
- **Budget rationale:** Routing logic and tests fit the logistics service pair.

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
  - backend/app/services/rag_policy.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add typed assistant intent routing. |
| `backend/tests/services/test_rag_logistics.py` | edit | Verify logistics, policy, mixed, and ambiguous routing. |

## Contract
Return intent `logistics|policy|mixed`, confidence, normalized tracking/order identifiers,
and routing reason. Explicit `SHP-####` or `PO-YYYY-###` selects logistics; policy-topic
terms select policy; both select mixed. Ambiguous operational questions without an
identifier return logistics with no guessed identifier.

## Environment Prerequisites
- C50 and C51 evidence contracts are frozen.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k intent -q
```

## Focused Tests
- Golden routing cases are stable.
- Identifiers normalize correctly.
- No identifier is invented.

## Done When
- [ ] Routing tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C56 assistant backend ready.

## Not In This Commit
- Retrieval orchestration or answer generation.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
