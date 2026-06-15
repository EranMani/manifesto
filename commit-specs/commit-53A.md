# Commit 53A - `budget-override-closeout-fix` - Claude

**Phase:** Logistics evidence (governance interrupt)
**Owner:** claude
**Depends on:** C52A
**Executor:** Claude-direct
**Estimated diff lines:** 320
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

`hooks/claude_budget.py`'s one-use override no longer deadlocks a Claude-direct
hard stop. `--authorize-override` grants up to 5 closeout-scoped uses, and a new
`is_closeout_action()` check restricts each use to telemetry correction,
verification, and finalization actions (read-only tools, edits under
`.context/telemetry/`, `.context/direct/`, `commit-protocol.md`,
`project-state.json`, or `/tests/`, and the existing control-command Bash
allowlist, now including `pytest`).

---

## Semantic Fit Review

- **Atomic outcome:** One governance bug (override exhausted after a single
  closeout action, re-deadlocking the hard stop) closed, with a bounded,
  category-restricted override and matching regression tests.
- **Failure boundary:** No change to the warn/stop thresholds, the
  `active_tokens` formula, or `allowed_after_stop`'s existing control-command
  allowlist beyond adding `pytest`.
- **Budget rationale:** Two small source files (116 diff lines combined,
  already implemented and tested), plus this spec and a one-row
  `commit-protocol.md` registration - four files total, fits within the
  standard 4-file / 350-line caps.

---

## Background

During C53's (`grounded-logistics-answer`, Nova, delegated) closeout, the
Claude-direct orchestrator scope hit its hard stop (40 actions). Eran approved
a one-use override (`--authorize-override`), but the prior implementation
(`authorize_override` set `uses_remaining: 1` with no category restriction)
was consumed by the very next tool call (a `Read` needed just to diagnose the
stop), immediately re-deadlocking every subsequent tool call - including the
reads needed to inspect and fix `claude_budget.py` itself.

Fixed by widening `authorize_override` to grant `uses_remaining: 5` and adding
`is_closeout_action(event)`, which restricts override consumption (when
`state == "stop"` and the action is not already covered by
`allowed_after_stop`) to: read-only tool calls (`Read`/`Grep`/`Glob`,
needed to diagnose and verify), and `Edit`/`Write`/`MultiEdit`/`NotebookEdit`
calls whose path falls under `.context/telemetry/`, `.context/direct/`,
`commit-protocol.md`, `project-state.json`, or `/tests/` (telemetry
correction, finalization artifacts, and test files). `pytest` was added to
the existing `CONTROL_COMMANDS` Bash allowlist (verification, always free,
mirroring `git status`/`git diff`).

C53's implementation files (`backend/app/services/rag_logistics.py`,
`backend/tests/services/test_rag_logistics.py`, `.context/direct/C53.md`,
Nova's worklog entry, and C53's telemetry records) remain unstaged and
unchanged by this commit; C53 finalizes immediately after, registered via the
normal commit-protocol.md / project-state.json replan that follows this
commit's close.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 2
  max_context_chars: 12000
  max_estimated_diff_lines: 350
  max_agent_invocations: 0
  max_tool_calls: 18
  max_expansions: 0
  max_implementor_tokens: 0
```

---

## Context

```yaml
primary_files:
  - hooks/claude_budget.py
  - hooks/tests/test_claude_budget.py
initial_context:
  - hooks/claude_budget.py
  - hooks/tests/test_claude_budget.py
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/claude_budget.py` | edit | Widen the budget override to 5 closeout-scoped uses via `is_closeout_action()`. |
| `hooks/tests/test_claude_budget.py` | edit | Regression tests for the closeout-scoped override and `is_closeout_action()`. |
| `commit-specs/commit-53A.md` | add | This specification. |
| `commit-protocol.md` | edit | Register C53A between C52A and C53. |

---

## Contract

A Claude-direct or delegated-review scope that hits a hard stop can be
unblocked by an explicitly approved override that covers the full closeout
sequence (inspect, correct telemetry, verify, finalize) without re-deadlocking
after a single tool call, while remaining restricted to closeout-shaped
actions - it cannot be used to resume open-ended implementation or research.

---

## Environment Prerequisites

- Run from the repository root. No Docker or application services required.

---

## Verification Command

```powershell
python -m pytest hooks/tests/test_claude_budget.py -q
```

---

## Focused Tests

- `authorize_override` sets `uses_remaining: 5`.
- A closeout-shaped action (e.g. `Edit` under `.context/telemetry/`, or any
  `Read`/`Grep`/`Glob`) consumes one override use at a hard stop and is
  allowed.
- A non-closeout action (e.g. `Edit` to an arbitrary source file) at a hard
  stop is blocked even with `uses_remaining > 0`, and the override is not
  consumed.
- `python hooks/claude_budget.py --authorize-override "..."` remains allowed
  after a hard stop via `allowed_after_stop`.

---

## Done When

- [x] `--authorize-override` grants up to 5 closeout-scoped uses.
- [x] `is_closeout_action()` gates override consumption to telemetry
      correction, verification, and finalization actions.
- [x] `pytest` is allowed after a hard stop without consuming an override.
- [x] `python -m pytest hooks/tests/test_claude_budget.py -q` passes (10/10).

---

## Developer Test Checkpoint

**Next milestone:** C53 (`grounded-logistics-answer`) finalizes immediately
after, using the corrected override to complete its review-telemetry
correction and verification.

---

## Not In This Commit

- C53 (`grounded-logistics-answer`) - implementation already complete and
  unstaged; finalizes immediately after this commit lands.
- No change to warn/stop thresholds or the `active_tokens` formula.
- `project-state.json` replan edits - applied separately as part of the
  chore(state) follow-up that advances to C53.

---

## Return Contract

### Human Summary
**What I completed:** Widened the Claude budget override from a single
unrestricted use to 5 closeout-scoped uses, gated by a new
`is_closeout_action()` check, with regression tests.
**What changed:** `hooks/claude_budget.py`, `hooks/tests/test_claude_budget.py`.
**What went wrong:** None.
**What remains:** None.
**Recommended next commit:** C53 (`grounded-logistics-answer`).
**Developer attention:** None.
