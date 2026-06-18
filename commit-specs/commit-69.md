# Commit 69 - `assistant-error-resilience` - Rex

**Phase:** Assistant hardening
**Owner:** rex
**Depends on:** C68
**Estimated diff lines:** 100
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Fix three backend bugs that produce HTTP 500 errors and misleading messages: catch unhandled embedding exceptions in policy/mixed answer generation, pass the LLM service to browse queries, and broaden the route handler's exception handling.

## Semantic Fit Review
- **Atomic outcome:** Policy queries that previously returned 500 now return a graceful fallback answer. Browse queries receive LLM-grounded responses.
- **Failure boundary:** Browse markdown formatting is C69A. Frontend markdown rendering remains C70. Intent classification fixes are C68.
- **Budget rationale:** Three targeted fixes across the assistant service and route handler, plus test updates, fit within 4 files.

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
  - backend/app/services/assistant.py
  - backend/app/api/v1/assistant.py
initial_context:
  - backend/app/services/assistant.py
  - backend/app/api/v1/assistant.py
  - backend/app/services/rag_policy.py
  - backend/app/services/rag_logistics.py
  - backend/tests/api/test_assistant.py
forbidden:
  - frontend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/assistant.py` | edit | Pass `llm` to browse handler. |
| `backend/app/api/v1/assistant.py` | edit | Broaden exception handling in route handler. |
| `backend/app/services/rag_policy.py` | edit | Catch embedding exceptions in `generate_grounded_policy_answer` and `generate_grounded_mixed_answer`. |
| `backend/tests/api/test_assistant.py` | edit | Update browse test assertion for new `llm` param; add catch-all exception test. |

## Contract

### Fix 1: Pass LLM to browse handler (`assistant.py`)
At line 60-62, change:
```python
return await generate_browse_logistics_answer(
    db, status_filter=routing.status_filter, question=message,
)
```
to:
```python
return await generate_browse_logistics_answer(
    db, llm=llm, status_filter=routing.status_filter, question=message,
)
```

### Fix 2: Catch embedding exceptions in policy answer generation (`rag_policy.py`)
In `generate_grounded_policy_answer` (line 329), wrap the `retrieve_evidence` call to catch `EmptyQueryError` and return the "not found" fallback:
```python
try:
    evidence = await policy.retrieve_evidence(db, text)
except EmptyQueryError:
    return PolicyAnswer(
        answer="The policy answer was not found in the available documents.",
        citations=[],
    )
```

In `generate_grounded_mixed_answer` (line 364), wrap `policy.retrieve_evidence` similarly — on `EmptyQueryError`, skip the policy section and return the logistics answer with empty citations:
```python
try:
    policy_evidence = await policy.retrieve_evidence(db, text)
except EmptyQueryError:
    policy_evidence = []
```

### Fix 3: Broaden route handler exception handling (`assistant.py` route)
At line 161, broaden the exception catch from `LLMError` only to also catch `Exception` as a last-resort handler that logs and returns a user-friendly 502:
```python
except LLMError:
    logger.exception("LLM provider error during assistant query")
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The AI service is temporarily unavailable. Please try again.",
    )
except Exception:
    logger.exception("Unexpected error during assistant query")
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Something went wrong processing your question. Please try again.",
    )
```

### Test updates (`test_assistant.py`)
- Update `test_browse_through_answer_question_returns_list` to assert `llm=mock_llm` in the `mock_browse.assert_called_once_with` call (Fix 1 changes the signature).
- Add `test_unexpected_error_returns_502` to verify the catch-all exception handler returns 502 with "Something went wrong" detail.

## Environment Prerequisites
- C68 complete (policy term expansion deployed).
- Backend test suite runnable via `docker compose run --rm backend uv run pytest`.

## Developer Test Checkpoint
**Next milestone:** C71 evidence graph timeline layout.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/api/test_assistant.py -x -q --tb=short
```

## Focused Tests
- Policy queries that previously 500'd now return a fallback answer.
- Browse queries call `generate_browse_logistics_answer` with `llm` parameter.
- Existing policy, logistics, and mixed tests still pass.
- Route handler catches unexpected exceptions gracefully.

## Done When
- [ ] `generate_browse_logistics_answer` receives `llm=llm` from `assistant.py`.
- [ ] `generate_grounded_policy_answer` catches `EmptyQueryError` gracefully.
- [ ] `generate_grounded_mixed_answer` catches `EmptyQueryError` gracefully.
- [ ] Route handler has a catch-all for unexpected exceptions.
- [ ] All existing assistant API tests pass.

## Not In This Commit
- Browse markdown formatting (C69A).
- Intent classification changes (C68).
- Frontend rendering or markdown (C70).
- Evidence graph changes (C71).

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
