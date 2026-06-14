# Commit 61 - `assistant-golden-evaluation` - Nova

**Phase:** Client demo verification
**Owner:** nova
**Depends on:** C60
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Evaluate the assistant against versioned golden logistics, policy, authorization, and fallback cases.

## Semantic Fit Review
- **Atomic outcome:** Demo correctness has one repeatable quality gate.
- **Failure boundary:** Clean stack rehearsal remains C62.
- **Budget rationale:** One dataset and one evaluation test fit two files.

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
  - backend/tests/services/fixtures/assistant_golden.json
  - backend/tests/services/test_assistant_golden.py
initial_context:
  - backend/app/services/assistant.py
  - backend/app/services/rag_logistics.py
  - backend/app/services/rag_policy.py
  - backend/tests/api/test_assistant.py
forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/models/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/tests/services/fixtures/assistant_golden.json` | add | Define 15-20 expected questions, facts, paths, and citations. |
| `backend/tests/services/test_assistant_golden.py` | add | Execute deterministic evidence-level evaluation. |

## Contract
Cover identifier lookup, buyer/vendor/products, timing, all exceptional outcomes,
follow-ups, unknown/ambiguous identifiers, policy, mixed, employee denial, and LLM
fallback. Require at least 90% exact expected-fact and relationship-path accuracy, with
authorization and leakage cases always passing.

## Environment Prerequisites
- C45-C60 assembled contracts are complete.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_assistant_golden.py -q
```

## Focused Tests
- Accuracy threshold is enforced.
- Every logistics claim maps to graph evidence.
- Policy citations and denial/fallback cases are exact.

## Done When
- [ ] Golden suite passes.
- [ ] Failures identify the exact case and missing fact/path.

## Developer Test Checkpoint
**Next milestone:** C62 client demo ready.

## Not In This Commit
- Browser automation or environment setup.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
