# Commit 56 - `unified-assistant-api` - Rex

**Phase:** Assistant backend
**Owner:** rex
**Depends on:** C55
**Estimated diff lines:** 320
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Expose one authenticated request/response endpoint for policy, logistics, and mixed questions.

## Semantic Fit Review
- **Atomic outcome:** The complete backend assistant is callable through one stable API.
- **Failure boundary:** Browser state and rendering remain C57-C60.
- **Budget rationale:** Schema, route, registration, and existing API test fit four files.

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
  - backend/app/api/v1/assistant.py
  - backend/app/schemas/assistant.py
initial_context:
  - backend/app/services/assistant.py
  - backend/app/main.py
  - backend/app/dependencies.py
  - backend/tests/api/test_assistant.py
forbidden:
  - frontend/
  - backend/app/models/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/schemas/assistant.py` | add | Define request, answer, citation, and graph schemas. |
| `backend/app/api/v1/assistant.py` | add | Implement authenticated POST `/api/v1/assistant/query`. |
| `backend/app/main.py` | edit | Register the assistant router. |
| `backend/tests/api/test_assistant.py` | edit | Verify all intents, validation, denial, and fallback responses. |

## Contract
Accept `{message, context[]}` with at most 12 prior turns and 8,000 total context
characters. Return `{intent, answer, graph|null, citations[], suggested_questions[]}`.
Blank/oversized input returns 422; unknown shipment returns a safe 404-style answer in a
200 response; provider failures use service fallbacks; authentication is mandatory.

## Environment Prerequisites
- C55 assistant orchestration is complete.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/api/test_assistant.py -q
```

## Focused Tests
- Logistics, policy, mixed, denial, unknown, and fallback payloads validate.
- Context limits reject unsafe requests.
- Unauthenticated requests return 401.

## Done When
- [ ] **Ready now:** One authenticated backend assistant API.
- [ ] **How to test:** Start the stack, login, and POST representative questions to `/api/v1/assistant/query`.
- [ ] **Expected result:** Correct intent, answer, and graph/citation evidence.
- [ ] **Still incomplete:** Browser experience begins C57.

## Developer Test Checkpoint
**Ready now:** Unified assistant backend.
**How to test:** Use the exact authenticated API request documented in the commit handoff.
**Expected result:** Logistics and policy questions return distinct evidence contracts.
**Still incomplete:** No integrated frontend.

## Not In This Commit
- Streaming, persistence, retries, or frontend.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
