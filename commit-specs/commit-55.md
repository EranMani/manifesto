# Commit 55 - `assistant-role-authorization` - Rex

**Phase:** Assistant backend
**Owner:** rex
**Depends on:** C54
**Estimated diff lines:** 190
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Enforce that employees may use policy evidence but cannot receive logistics evidence.

## Semantic Fit Review
- **Atomic outcome:** Role and intent produce one authorization decision.
- **Failure boundary:** HTTP exposure remains C56.
- **Budget rationale:** One orchestration service and API-focused test fit two files.

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
  - backend/tests/api/test_assistant.py
initial_context:
  - backend/app/dependencies.py
  - backend/app/models/user.py
  - backend/app/services/rag_logistics.py
  - backend/app/services/rag_policy.py
forbidden:
  - frontend/
  - backend/app/api/v1/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/assistant.py` | add | Orchestrate routing and enforce role access. |
| `backend/tests/api/test_assistant.py` | add | Verify role/intent authorization without an endpoint. |

## Contract
`answer_question(user_role, message, context, ...)` permits policy for all active roles,
logistics/mixed only for manager/admin, and returns a generic denial with no retrieval
calls or operational identifiers for employee logistics attempts.

## Environment Prerequisites
- C52-C54 routing and answer services are available.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/api/test_assistant.py -k authorization -q
```

## Focused Tests
- Employee policy requests proceed.
- Employee logistics/mixed requests retrieve nothing and leak nothing.
- Manager/admin requests proceed.

## Done When
- [ ] Authorization tests pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C56 assistant backend ready.

## Not In This Commit
- Request schemas or route registration.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
