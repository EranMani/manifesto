# Commit 74 - `citations-ui` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C73
**Estimated diff lines:** 255
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Render safe ordered provenance for completed live and historical messages.

---

## Semantic Fit Review

- **Atomic outcome:** One frontend transport, state, component, or integration outcome is introduced.
- **Failure boundary:** Later visual or data behavior remains independently testable.
- **Budget rationale:** 3 exact changed file(s), 5 initial context file(s), and one focused verification command fit one bounded invocation.

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
  - frontend/src/components/chat/Citations.tsx
  - frontend/src/components/chat/StreamingMessage.tsx
initial_context:
  - commit-specs/commit-74.md
  - frontend/src/components/chat/Citations.tsx
  - frontend/src/components/chat/StreamingMessage.tsx
  - frontend/src/components/chat/Citations.test.tsx
  - commit-specs/commit-73.md
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/components/chat/Citations.tsx` | new | Render semantic source list |
| `frontend/src/components/chat/StreamingMessage.tsx` | edit | Attach completed citations |
| `frontend/src/components/chat/Citations.test.tsx` | new | Prove live, history, dedupe, and safety |

---

## Contract

Render safe ordered provenance for completed live and historical messages.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run src/components/chat/Citations.test.tsx
```

---

## Focused Tests

- Live and reloaded sources match.
- Failed, cancelled, empty, and duplicate sources remain safe.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** Live and historical citation rendering is ready.
**How to test:** Ask a policy question, wait for completion, inspect Sources, then reload the conversation.
**Expected result:** The same safe ordered provenance appears live and after reload.
**Still incomplete:** The assembled end-to-end smoke remains C76.

---

## Not In This Commit

- Full mocked integration is C75.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
