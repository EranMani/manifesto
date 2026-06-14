# Commit 51 - `minimal-policy-evidence` - Nova

**Phase:** Assistant backend
**Owner:** nova
**Depends on:** C50
**Estimated diff lines:** 250
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Retrieve ready policy chunks with source labels using the existing vector channel.

## Semantic Fit Review
- **Atomic outcome:** Policy questions receive bounded cited evidence without advanced fusion.
- **Failure boundary:** Answer generation remains C54.
- **Budget rationale:** Existing policy service/test pair contains the minimum path.

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
  - backend/app/models/policy.py
  - backend/app/services/llm.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_policy.py` | edit | Add DB-backed minimal evidence retrieval and citations. |
| `backend/tests/services/test_rag_policy.py` | edit | Verify profile filtering, labels, threshold, and limits. |

## Contract
Embed once, retrieve at most five ready profile-matched chunks, discard scores below
`0.35`, and return source title, document/chunk IDs, section, page, excerpt, and score.
Do not add lexical fusion, diversification, or metrics.

## Environment Prerequisites
- C46 bundled policies are ready.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_policy.py -k minimal_evidence -q
```

## Focused Tests
- Ready matching chunks return source labels.
- Wrong profiles and weak evidence are excluded.
- Result count is bounded.

## Done When
- [ ] Minimal evidence contract passes.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C56 assistant backend ready.

## Not In This Commit
- Lexical fusion, answer generation, or HTTP.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
