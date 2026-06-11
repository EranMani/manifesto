# Commit 29C - `preflight-dashboard-details` - Adam

**Phase:** Workflow Preflight
**Owner:** adam
**Depends on:** C29B
**Estimated diff lines:** 280
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Display each commit's deterministic preflight score and expandable report details inside
the dashboard Context Efficiency table.

---

## Semantic Fit Review

- **Atomic outcome:** One visual surface makes persisted Python preflight evidence inspectable per commit.
- **Failure boundary:** Dashboard failure cannot change or bypass the preflight decision.
- **Budget rationale:** Three exact changed files and one focused dashboard test command fit one invocation.

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
  - hooks/preflight_commit.py
initial_context:
  - hooks/constraint_dashboard.py
  - hooks/preflight_commit.py
  - hooks/tests/test_context_telemetry.py
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/constraint_dashboard.py` | edit | Load reports and render score plus expandable details |
| `hooks/preflight_commit.py` | edit | Refresh the dashboard after persisting a report |
| `hooks/tests/test_context_telemetry.py` | edit | Verify score badges, details, and missing-report behavior |

---

## Contract

The dashboard reads `.context/preflight/C<ID>.json` as observational data. Each commit
row in the Context Efficiency table shows:

- Confidence/readiness score from 0 to 100.
- `READY`, `WARNING`, or `BLOCKED` from the persisted `proceed` result.
- Blocking-violation and warning counts.
- `NOT RUN` when no report exists.

Clicking the commit row expands a detail panel containing:

- Score-category breakdown and deductions.
- Blocking violations with rule, evidence, and repair direction.
- Warnings.
- Planned files, generated context package, budgets, dependencies, prerequisites, and
  verification-command evidence.
- Report fingerprint/path when available.
- A collapsible, escaped JSON view of the exact persisted report.

All report content is HTML-escaped. Missing or malformed reports render as `NOT RUN` or
`INVALID REPORT` and never crash dashboard generation.

The dashboard does not recalculate confidence and cannot override `proceed`. Python
remains the sole authority. A completed preflight refreshes the dashboard so the current
commit appears without a separate manual render.

---

## Environment Prerequisites

- C29A's report schema and persistence, and C29B's delegation gate, are complete.
- Python hook test environment.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_context_telemetry.py -q
```

---

## Focused Tests

- Ready, warning, and blocked scores render with distinct labels.
- Clicking a row exposes score breakdown and exact escaped report.
- Blocking violations and repair directions remain readable.
- Missing and malformed reports degrade safely.
- Dashboard rendering never changes the persisted decision.
- Preflight persistence triggers dashboard refresh.

---

## Done When

- [ ] Every available report is associated with its commit row.
- [ ] Score, status, warnings, and blockers are visible without raw-file inspection.
- [ ] Row expansion exposes readable details and exact escaped JSON.
- [ ] Missing or invalid reports cannot break dashboard generation.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C32.

---

## Not In This Commit

- Changing score weights, threshold, or hard-block rules.
- Allowing the dashboard to approve or bypass delegation.
- Historical trend charts across repeated preflight executions.
- Changes to C30-C76 feature behavior.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. Confirm the
dashboard renders the persisted report without recalculating or mutating its decision.
If completion is not credible by call 16, stop and return `SPLIT_REQUIRED`.
