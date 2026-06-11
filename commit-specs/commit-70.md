# Commit 70 - `provider-selection-ui` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C69
**Estimated diff lines:** 255
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Require and lock provider selection for a new policy conversation.

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
  - frontend/src/components/chat/ProviderSelectModal.tsx
  - frontend/src/pages/ChatPolicy.tsx
initial_context:
  - commit-specs/commit-70.md
  - frontend/src/components/chat/ProviderSelectModal.tsx
  - frontend/src/pages/ChatPolicy.tsx
  - frontend/src/pages/ChatPolicy.test.tsx
  - commit-specs/commit-69.md
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/components/chat/ProviderSelectModal.tsx` | new | Implement accessible provider selection |
| `frontend/src/pages/ChatPolicy.tsx` | edit | Assemble basic visible policy chat |
| `frontend/src/pages/ChatPolicy.test.tsx` | new | Prove selection lock and basic chat workflow |

---

## Contract

Require and lock provider selection for a new policy conversation.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run src/pages/ChatPolicy.test.tsx
```

---

## Focused Tests

- New conversation requires provider choice.
- Provider locks after first send.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** Basic visible Policy Chat is ready.
**How to test:** Run `docker compose up -d`, open `/chat/policy`, choose a provider, send a message, stop a stream, and retry safely.
**Expected result:** Provider selection, incremental text, stop, and safe retry are visible and usable.
**Still incomplete:** Conversation history and citations remain C71-C74.

---

## Not In This Commit

- Conversation history starts C71.
- Citations are C74.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
