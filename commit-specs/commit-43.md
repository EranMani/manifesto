# Commit 43 - `policy-evidence-threshold` - Nova

**Phase:** Policy RAG
**Owner:** nova
**Depends on:** C42
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Return an abstention decision when evidence is below threshold.

---

## Semantic Fit Review

- **Atomic outcome:** One decision boundary separates answerable from unsupported queries.
- **Failure boundary:** Context selection remains C44.
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
  - backend/app/services/rag_policy.py
initial_context:
  - backend/app/services/rag_policy.py
  - backend/tests/services/test_rag_policy.py
forbidden:
  - backend/app/api/
  - backend/app/models/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_policy.py` | edit | Return an abstention decision when evidence is below threshold. |
| `backend/tests/services/test_rag_policy.py` | edit | Prove policy-evidence-threshold |

---

## Contract

Return an abstention decision when evidence is below threshold.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C37 ingestion database contract and C25 provider-neutral services are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_policy.py -k evidence_threshold -q
```

---

## Focused Tests

- Strong evidence proceeds.
- Weak or empty evidence abstains.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C49.

---

## Not In This Commit

- Later policy RAG behavior starts C44.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
