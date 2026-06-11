# Commit 69 - `message-input-cancel` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C68
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Provide accessible submit, stop, and safe retry controls.

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
  - frontend/src/components/chat/MessageInput.tsx
initial_context:
  - commit-specs/commit-69.md
  - frontend/src/components/chat/MessageInput.tsx
  - frontend/src/components/chat/MessageInput.test.tsx
  - commit-specs/commit-68.md
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/components/chat/MessageInput.tsx` | new | Implement composer and controls |
| `frontend/src/components/chat/MessageInput.test.tsx` | new | Prove keyboard, busy, stop, and retry behavior |

---

## Contract

Provide accessible submit, stop, and safe retry controls.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run src/components/chat/MessageInput.test.tsx
```

---

## Focused Tests

- Keyboard submit and multiline behavior work.
- Stop aborts and retry reuses the client message ID.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C70.

---

## Not In This Commit

- Provider selection and page assembly are C70.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
