# Commit 54 - `grounded-policy-answer` - Nova

**Phase:** Assistant backend
**Owner:** nova
**Depends on:** C53
**Estimated diff lines:** 240
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Generate grounded policy and mixed answers with distinct policy citations and logistics evidence.

## Semantic Fit Review
- **Atomic outcome:** Non-logistics-only intents receive one grounded response contract.
- **Failure boundary:** Role enforcement remains C55.
- **Budget rationale:** Policy generation and tests fit the policy service pair.

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
  - backend/app/services/rag_policy.py
  - backend/tests/services/test_rag_policy.py
initial_context:
  - backend/app/services/rag_policy.py
  - backend/tests/services/test_rag_policy.py
  - backend/app/services/rag_logistics.py
  - backend/app/services/llm.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_policy.py` | edit | Add policy and mixed grounded generation. |
| `backend/tests/services/test_rag_policy.py` | edit | Verify citations, insufficient evidence, and mixed provenance. |

## Contract
Policy answers use only C51 evidence and return source citations. If evidence is absent,
state that the policy answer was not found. Mixed answers combine a supplied logistics
answer/evidence payload with policy excerpts while preserving separate `graph` and
`citations` fields. `LLMError` returns an evidence excerpt summary, never invented policy.

## Environment Prerequisites
- C53 logistics answer and C51 policy evidence contracts are frozen.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_policy.py -k grounded_answer -q
```

## Focused Tests
- Citations match retrieved chunks.
- Insufficient evidence is explicit.
- Mixed provenance remains separate.

## Done When
- [ ] Grounding tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C56 assistant backend ready.

## Not In This Commit
- Authorization or HTTP.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
