# Commit 65 - `frontend-test-baseline` - Aria

**Phase:** Frontend Policy Chat
**Owner:** aria
**Depends on:** C64
**Estimated diff lines:** 310
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Install and prove one focused frontend component-test command.

---

## Semantic Fit Review

- **Atomic outcome:** One frontend transport, state, component, or integration outcome is introduced.
- **Failure boundary:** Later visual or data behavior remains independently testable.
- **Budget rationale:** 4 exact changed file(s), 5 initial context file(s), and one focused verification command fit one bounded invocation.

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
  - frontend/package.json
  - frontend/vite.config.ts
initial_context:
  - frontend/package.json
  - frontend/vite.config.ts
  - frontend/src/test/setup.ts
forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/package.json` | edit | Add Vitest scripts and dependencies |
| `frontend/package-lock.json` | new | Lock test dependencies |
| `frontend/vite.config.ts` | edit | Configure Vitest and jsdom |
| `frontend/src/test/setup.ts` | new | Install shared DOM matchers |

---

## Contract

Install and prove one focused frontend component-test command.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C65 test baseline for C66 and later.
- Backend contracts through C64 are frozen.

---

## Verification Command

```powershell
cd frontend; npm test -- --run
```

---

## Focused Tests

- A trivial DOM test runs.
- The command exits nonzero on failure.

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

- No policy-chat behavior until C66.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
