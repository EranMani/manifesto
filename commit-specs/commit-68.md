# Commit 68 - `policy-term-expansion` - Nova

**Phase:** Assistant hardening
**Owner:** nova
**Depends on:** C67
**Estimated diff lines:** 120
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Expand the intent classifier's policy vocabulary so queries about employee leave, HR rules, benefits, vendor performance, and other policy-adjacent topics route to the policy handler instead of falling through to the logistics default.

## Semantic Fit Review
- **Atomic outcome:** Policy-adjacent queries classify as `policy` instead of defaulting to `logistics` with 0.5 confidence.
- **Failure boundary:** Error handling for unhandled exceptions remains C69. Frontend rendering changes remain C70-C71.
- **Budget rationale:** One term list expansion, one golden test fixture update, and corresponding unit test assertions fit two files.

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
  - backend/app/services/assistant.py
  - backend/tests/services/fixtures/assistant_golden.json
forbidden:
  - frontend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Expand `_POLICY_TERMS` frozenset with additional terms. |
| `backend/tests/services/test_rag_logistics.py` | edit | Add intent routing tests for newly covered policy queries. |
| `backend/tests/services/fixtures/assistant_golden.json` | edit | Add golden cases for employee leave, vendor performance, and HR queries. |

## Contract

### Policy term expansion (`rag_logistics.py`)
Add the following terms to `_POLICY_TERMS` (lines 758-778):
- `"rules"`, `"rule"` — covers "What are the employee leave rules?"
- `"leave"`, `"leaves"` — covers employee leave queries
- `"employee"`, `"employees"` — covers HR-scoped questions
- `"benefits"`, `"benefit"` — covers benefits inquiries
- `"vacation"`, `"sick"`, `"absence"` — covers specific leave types
- `"schedule"`, `"scheduling"` — covers scheduling policy
- `"safety"`, `"training"` — covers workplace policy
- `"hr"` — direct HR references

These terms are all unambiguously policy-scoped: they never appear in legitimate logistics-only queries. The existing priority order (identifier > policy > browse > default) is unchanged.

### Intent routing for "Summarize vendor performance this month"
The query "Summarize vendor performance this month" contains "vendor" which is not a policy term (vendors are logistics entities). However, "performance" in a non-tracking-code context is a policy/reporting query. Add `"performance"` to `_POLICY_TERMS`. Combined with the absence of any tracking code or browse term, this routes correctly to policy.

### No changes to the default fallback
The default fallback (confidence 0.5 → logistics) remains for truly ambiguous queries. The expansion reduces the set of queries that reach this fallback, but does not eliminate it.

### Test additions (`test_rag_logistics.py`)
Add `test_intent_routing_*` functions:
- `"What are the employee leave rules?"` → intent `"policy"`, confidence `1.0`
- `"Summarize vendor performance this month"` → intent `"policy"`, confidence `1.0`
- `"What are the benefits for new employees?"` → intent `"policy"`, confidence `1.0`
- `"Tell me about the vacation policy"` → intent `"policy"`, confidence `1.0`
- `"What are the safety training rules?"` → intent `"policy"`, confidence `1.0`

### Golden test additions (`assistant_golden.json`)
Add cases:
- `"policy-employee-leave"`: question "What are the employee leave rules?", role "employee", expected_intent "policy"
- `"policy-vendor-performance"`: question "Summarize vendor performance this month", role "manager", expected_intent "policy"

## Environment Prerequisites
- C67 complete (evidence graph visual overhaul deployed).
- Backend test suite runnable via `docker compose run --rm backend uv run pytest`.

## Developer Test Checkpoint
**Next milestone:** C71 evidence graph timeline layout.

## Verification Command
```powershell
python -m pytest backend/tests/services/test_rag_logistics.py -x -q --tb=short -k "intent_routing"
```

## Focused Tests
- All existing intent routing tests still pass (no regressions).
- New policy-term queries classify as `policy` with confidence `1.0`.
- Browse queries remain unaffected (e.g., "Show delayed shipments" still routes to `logistics_browse`).
- Logistics queries with tracking codes remain unaffected.

## Done When
- [ ] `_POLICY_TERMS` includes all added terms.
- [ ] "What are the employee leave rules?" classifies as `policy`.
- [ ] "Summarize vendor performance this month" classifies as `policy`.
- [ ] All existing intent routing tests pass without modification.

## Not In This Commit
- Error handling for embedding/LLM failures (C69).
- Frontend rendering changes (C70-C71).
- New intent types or fallback UI.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
