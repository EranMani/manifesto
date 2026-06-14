# Commit 57 - `assistant-client-session-state` - Aria

**Phase:** Integrated prototype
**Owner:** aria
**Depends on:** C56
**Estimated diff lines:** 240
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Provide a typed frontend assistant client and session-only message state.

## Semantic Fit Review
- **Atomic outcome:** The browser can send questions and retain current-session turns.
- **Failure boundary:** Visual conversation UI remains C59.
- **Budget rationale:** One API module and one Zustand store fit two files.

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
  - frontend/src/api/assistant.ts
  - frontend/src/store/assistant.ts
initial_context:
  - frontend/src/api/client.ts
  - frontend/src/store/auth.ts
  - backend/app/schemas/assistant.py
forbidden:
  - backend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/assistant.ts` | add | Mirror the unified assistant wire types and POST call. |
| `frontend/src/store/assistant.ts` | add | Hold session messages, loading, errors, and current evidence. |

## Contract
Store user/assistant turns in memory only. Sending includes at most the last 12 turns,
prevents concurrent sends, appends a user turn immediately, appends the validated response,
and exposes a reset action. Do not use localStorage.

## Environment Prerequisites
- C56 API schema is frozen.

## Verification Command
```powershell
npm --prefix frontend run build
```

## Focused Tests
- TypeScript validates wire types and store transitions.
- Session reset clears messages/evidence.

## Done When
- [ ] Frontend build passes.
- [ ] State remains session-only.

## Developer Test Checkpoint
**Next milestone:** C60 integrated prototype ready.

## Not In This Commit
- Graph rendering or page layout.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
