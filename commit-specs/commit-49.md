# Commit 49 - `policy-citation-validation` - Nova

**Phase:** Policy RAG
**Owner:** nova
**Depends on:** C48
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Accept only citation labels present in selected evidence.

---

## Semantic Fit Review

- **Atomic outcome:** One validator checks generated citations against frozen source labels.
- **Failure boundary:** Offline evaluation remains C50-C53.
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
  - commit-specs/commit-49.md
  - backend/app/services/rag_policy.py
  - backend/tests/services/test_rag_policy.py
  - commit-specs/commit-48.md
forbidden:
  - backend/app/api/
  - backend/app/models/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_policy.py` | edit | Accept only citation labels present in selected evidence. |
| `backend/tests/services/test_rag_policy.py` | edit | Prove policy-citation-validation |

---

## Contract

Accept only citation labels present in selected evidence.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C37 ingestion database contract and C25 provider-neutral services are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_policy.py -k citation_validation -q
```

---

## Focused Tests

- Known labels resolve to sources.
- Unknown labels are rejected or removed.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** The complete policy RAG service contract is ready for focused testing.
**How to test:** Run `docker compose run --rm backend uv run pytest tests/services/test_rag_policy.py -q`.
**Expected result:** Retrieval, ranking, grounding, streaming, cancellation, and citation validation pass.
**Still incomplete:** Offline evaluation and HTTP exposure remain C50-C56.

---

## Not In This Commit

- Offline evaluation starts C50.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
