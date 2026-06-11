# Commit 72 - `conversation-sidebar-list` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C71
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Render paginated policy conversation navigation.

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
  - frontend/src/components/chat/ConversationSidebar.tsx
initial_context:
  - frontend/src/components/chat/ConversationSidebar.tsx
  - frontend/src/components/chat/ConversationSidebar.test.tsx
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/components/chat/ConversationSidebar.tsx` | new | Render list, paging, loading, and empty states |
| `frontend/src/components/chat/ConversationSidebar.test.tsx` | new | Prove list and pagination behavior |

---

## Contract

Render paginated policy conversation navigation.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run src/components/chat/ConversationSidebar.test.tsx
```

---

## Focused Tests

- Empty, loading, error, and list states render.
- Pagination preserves stable ordering.

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

- URL history navigation is C73.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
