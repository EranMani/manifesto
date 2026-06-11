# Commit 53 - `policy-runtime-baselines` - Nova

**Phase:** Policy RAG
**Owner:** nova
**Depends on:** C52
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Record deterministic context-size and latency baseline summaries.

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
  - commit-specs/commit-53.md
  - backend/tests/services/policy_rag_evaluation.py
  - backend/tests/services/test_rag_policy_evaluation.py
  - commit-specs/commit-52.md
forbidden:
  - backend/app/api/
  - backend/app/models/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/tests/services/policy_rag_evaluation.py` | edit | Summarize runtime measurements |
| `backend/tests/services/test_rag_policy_evaluation.py` | edit | Prove baseline summaries |

---

## Contract

Record deterministic context-size and latency baseline summaries.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C49 validated policy RAG service available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_policy_evaluation.py -k runtime_baselines -q
```

---

## Focused Tests

- Percentile and context summaries are stable.
- Missing timing remains unknown rather than zero.

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

- HTTP route exposure starts C54.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
