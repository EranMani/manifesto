# Commit 31 - `telemetry-reconciliation` - Adam

**Phase:** Workflow Trust
**Owner:** adam
**Depends on:** C30
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Aggregate commit telemetry while explicitly reporting contradictions and unknown values.

---

## Semantic Fit Review

- **Atomic outcome:** One reconciliation result is produced from existing immutable records.
- **Failure boundary:** HTML presentation remains C32.
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
  - hooks/context_metrics.py
initial_context:
  - hooks/context_metrics.py
  - hooks/tests/test_context_telemetry.py
forbidden:
  - backend/app/
  - frontend/src/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/context_metrics.py` | edit | Aggregate records and contradiction evidence |
| `hooks/tests/test_context_telemetry.py` | edit | Prove reconciliation and unknown handling |

---

## Contract

Aggregate commit telemetry while explicitly reporting contradictions and unknown values.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C30 invocation records available.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_context_telemetry.py -q
```

---

## Focused Tests

- Matching sources reconcile.
- Conflicting or absent totals remain explicit.

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

- Dashboard ledger is C32.
- Historical evidence is not rewritten.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
