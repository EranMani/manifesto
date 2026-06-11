# Commit 40 - `policy-lexical-candidates` - Nova

**Phase:** Policy RAG
**Owner:** nova
**Depends on:** C39
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Fetch ready, profile-matched lexical candidates.

---

## Semantic Fit Review

- **Atomic outcome:** One full-text retrieval channel returns ranked candidates.
- **Failure boundary:** Fusion remains C41.
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
  - commit-specs/commit-40.md
  - backend/app/services/rag_policy.py
  - backend/tests/services/test_rag_policy.py
  - commit-specs/commit-39.md
forbidden:
  - backend/app/api/
  - backend/app/models/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_policy.py` | edit | Fetch ready, profile-matched lexical candidates. |
| `backend/tests/services/test_rag_policy.py` | edit | Prove policy-lexical-candidates |

---

## Contract

Fetch ready, profile-matched lexical candidates.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C37 ingestion database contract and C25 provider-neutral services are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_policy.py -k lexical_candidates -q
```

---

## Focused Tests

- Text rank ordering is deterministic.
- Wrong-profile and non-ready documents are excluded.

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

- Later policy RAG behavior starts C41.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
