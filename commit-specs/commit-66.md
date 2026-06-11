# Commit 66 - `chat-sse-client` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C65
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Parse authenticated POST SSE events across arbitrary transport chunks.

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
  - frontend/src/api/chat.ts
initial_context:
  - commit-specs/commit-66.md
  - frontend/src/api/chat.ts
  - frontend/src/api/chat.test.ts
  - commit-specs/commit-65.md
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/chat.ts` | new | Implement typed POST SSE client |
| `frontend/src/api/chat.test.ts` | new | Prove framing, Unicode, errors, and abort |

---

## Contract

Parse authenticated POST SSE events across arbitrary transport chunks.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run src/api/chat.test.ts
```

---

## Focused Tests

- Fragmented and coalesced events parse.
- Malformed ordering and versions fail safely.

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

- No visible chat state until C67.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
