# Commit 51 - `policy-retrieval-metrics` - Nova

**Phase:** Policy RAG
**Owner:** nova
**Depends on:** C50
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Calculate retrieval hit rate and mean reciprocal rank from evaluation results.

---

## Semantic Fit Review

- **Atomic outcome:** One offline evaluation artifact or metric is introduced.
- **Failure boundary:** Other metric families remain separate.
- **Budget rationale:** 2 exact changed file(s), 4 initial context file(s), and one focused verification command fit one bounded invocation.

---

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

---

## Context

```yaml
primary_files:
  - backend/tests/services/policy_rag_evaluation.py
initial_context:
  - commit-specs/commit-51.md
  - backend/tests/services/policy_rag_evaluation.py
  - backend/tests/services/test_rag_policy_evaluation.py
  - commit-specs/commit-50.md
forbidden:
  - backend/app/api/
  - backend/app/models/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/tests/services/policy_rag_evaluation.py` | new | Implement retrieval metrics |
| `backend/tests/services/test_rag_policy_evaluation.py` | edit | Prove metric calculations |

---

## Contract

Calculate retrieval hit rate and mean reciprocal rank from evaluation results.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C49 validated policy RAG service available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_policy_evaluation.py -k retrieval_metrics -q
```

---

## Focused Tests

- Hit rate and MRR match fixed examples.
- Empty results produce defined zeros.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C56.

---

## Not In This Commit

- Answer-quality metrics are C52.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
