# Commit 30 - `invocation-record-storage` - Adam

**Phase:** Workflow Trust
**Owner:** adam
**Depends on:** C29C
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Store each normal, repair, and review invocation as a separate immutable telemetry record.

---

## Semantic Fit Review

- **Atomic outcome:** One storage contract: append one invocation without flattening prior records.
- **Failure boundary:** Aggregation and dashboard rendering remain separate.
- **Budget rationale:** 2 exact changed file(s), 3 initial context file(s), and one focused verification command fit one bounded invocation.

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
  - hooks/context_telemetry.py
initial_context:
  - commit-specs/commit-30.md
  - hooks/context_telemetry.py
  - hooks/tests/test_telemetry_scopes.py
forbidden:
  - backend/app/
  - frontend/src/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/context_telemetry.py` | edit | Persist immutable invocation records |
| `hooks/tests/test_telemetry_scopes.py` | edit | Prove append-only invocation storage |

---

## Contract

Store each normal, repair, and review invocation as a separate immutable telemetry record.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Python hook test environment.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_telemetry_scopes.py -q
```

---

## Focused Tests

- Normal, repair, and review records append independently.
- Finalization cannot overwrite a prior invocation.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C32.

---

## Not In This Commit

- Commit aggregation is C31.
- Dashboard presentation is C32.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
