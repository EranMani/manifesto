# Commit 53 - `grounded-logistics-answer` - Nova

**Phase:** Assistant backend
**Owner:** nova
**Depends on:** C52
**Estimated diff lines:** 250
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Generate a grounded logistics answer from structured evidence with a deterministic fallback.

## Semantic Fit Review
- **Atomic outcome:** Logistics evidence becomes one safe verbal response.
- **Failure boundary:** Policy/mixed answering remains C54.
- **Budget rationale:** Generation and tests fit the logistics service pair.

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
  - backend/app/services/llm.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add evidence-bounded OpenAI prompt and fallback formatter. |
| `backend/tests/services/test_rag_logistics.py` | edit | Verify grounding and provider failure behavior. |

## Contract
Build a provider-neutral prompt containing only retrieved evidence and session context.
Return complete answer text, graph evidence, and suggested follow-ups. On any `LLMError`,
return a deterministic summary of status, reason, vendor, buyer/order, products, and timing.
Never expose SQL or claim fields absent from evidence.

## Environment Prerequisites
- C52 routing and C50 graph evidence exist.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k grounded_answer -q
```

## Focused Tests
- Prompt contains only evidence.
- Successful output keeps graph unchanged.
- Provider failure returns the deterministic fallback.

## Done When
- [ ] Answer and fallback tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C56 assistant backend ready.

## Not In This Commit
- Policy answers or HTTP.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
