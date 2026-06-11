# Commit 32 - `telemetry-dashboard-ledger` - Adam

**Phase:** Workflow Trust
**Owner:** adam
**Depends on:** C31
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Render the invocation ledger and commit budget state in the constraint dashboard.

---

## Semantic Fit Review

- **Atomic outcome:** One operator view consumes the reconciled telemetry contract.
- **Failure boundary:** Telemetry storage and reconciliation are already frozen.
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
  - hooks/constraint_dashboard.py
initial_context:
  - hooks/constraint_dashboard.py
  - hooks/tests/test_context_telemetry.py
forbidden:
  - backend/app/
  - frontend/src/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/constraint_dashboard.py` | edit | Render ledger and budget states |
| `hooks/tests/test_context_telemetry.py` | edit | Prove dashboard ledger output |

---

## Contract

Render the invocation ledger and commit budget state in the constraint dashboard.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C31 reconciled metric shape available.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_context_telemetry.py -q
```

---

## Focused Tests

- Separate invocations render.
- Contradictions and unknown tokens are visible.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** The invocation-ledger dashboard is ready for inspection.
**How to test:** Run `python hooks/render_constraint_dashboard.py`, then open `constraint-dashboard.html`.
**Expected result:** Each invocation appears separately with totals, budget state, and contradiction indicators.
**Still incomplete:** Product and database recovery work begins in C33.

---

## Not In This Commit

- Product recovery begins C33.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
