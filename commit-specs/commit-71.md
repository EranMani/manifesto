# Commit 71 - `conversation-api-client` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C70
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Consume typed conversation-list and history API contracts.

---

## Semantic Fit Review

- **Atomic outcome:** One frontend transport, state, component, or integration outcome is introduced.
- **Failure boundary:** Later visual or data behavior remains independently testable.
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
  - frontend/src/api/conversations.ts
initial_context:
  - frontend/src/api/conversations.ts
  - frontend/src/api/conversations.test.ts
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/conversations.ts` | new | Implement typed list and history calls |
| `frontend/src/api/conversations.test.ts` | new | Prove cursor and history parsing |

---

## Contract

Consume typed conversation-list and history API contracts.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run src/api/conversations.test.ts
```

---

## Focused Tests

- List cursors and message pages parse.
- Malformed response shapes fail safely.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C73.

---

## Not In This Commit

- Sidebar presentation is C72.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
