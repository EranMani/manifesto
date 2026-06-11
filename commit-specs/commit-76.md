# Commit 76 - `assembled-policy-chat-smoke` - Adam

**Phase:** Assembled Verification
**Owner:** adam
**Depends on:** C75
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Prove upload, ask, stream, reload, and citations through the assembled application stack.

---

## Semantic Fit Review

- **Atomic outcome:** One smoke workflow verifies integration without adding product behavior.
- **Failure boundary:** Feature defects become new owner-specific commits rather than smoke-script fixes.
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
  - scripts/smoke_policy_chat.ps1
initial_context:
  - scripts/smoke_policy_chat.ps1
  - SMOKE_TEST_RESULTS.md
forbidden:
  - backend/app/
  - frontend/src/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `scripts/smoke_policy_chat.ps1` | new | Automate assembled Phase 2 smoke |
| `SMOKE_TEST_RESULTS.md` | edit | Record commands and expected evidence |

---

## Contract

Prove upload, ask, stream, reload, and citations through the assembled application stack.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker stack, Ollama model, and browser access available.

---

## Verification Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_policy_chat.ps1
```

---

## Focused Tests

- Upload a policy, ask a question, observe streaming, reload history, and inspect citations.
- Failures identify the owning boundary without hiding them.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** The complete Phase 2 policy-chat workflow is ready.
**How to test:** Run `scripts/smoke_policy_chat.ps1`, then repeat upload -> ask -> stream -> reload -> citations in the browser.
**Expected result:** The assembled stack completes the full workflow with durable history and citations.
**Still incomplete:** No Phase 2 policy-chat behavior remains.

---

## Not In This Commit

- No product fixes.
- No Phase 3 logistics work.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
