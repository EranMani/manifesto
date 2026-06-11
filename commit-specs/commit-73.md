# Commit 73 - `conversation-history-navigation` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C72
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Make URL-selected conversation history race-safe and reloadable.

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
  - frontend/src/pages/ChatPolicy.tsx
initial_context:
  - frontend/src/pages/ChatPolicy.tsx
  - frontend/src/pages/ChatPolicy.history.test.tsx
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/ChatPolicy.tsx` | edit | Integrate sidebar, URL selection, and history loading |
| `frontend/src/pages/ChatPolicy.history.test.tsx` | new | Prove reload, back/forward, and stale-response safety |

---

## Contract

Make URL-selected conversation history race-safe and reloadable.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run src/pages/ChatPolicy.history.test.tsx
```

---

## Focused Tests

- Deep links and reload restore history.
- Late responses cannot replace the current conversation.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** Conversation history navigation is ready.
**How to test:** Open `/chat/policy`, select conversations in the sidebar, reload, and use browser back/forward.
**Expected result:** The URL-selected conversation reloads correctly and stale responses cannot replace the active selection.
**Still incomplete:** Citation presentation remains C74.

---

## Not In This Commit

- Citation presentation is C74.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
