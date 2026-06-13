# Commit 33B - `finalize-commit-pipeline` - Claude

**Phase:** Workflow Redesign - Stop the Bleeding
**Owner:** claude
**Depends on:** C33A
**Execution mode:** Claude-direct
**Estimated diff lines:** 480
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

A single deterministic pipeline (`hooks/finalize_commit.py`) runs the post-test-pass
sequence in one fixed order — verify constraints, optional dashboard render, write the
notify flag, write a finalize marker — and `pre_commit_check.py` fails closed on a
primary commit unless that marker exists and matches.

---

## Semantic Fit Review

- **Atomic outcome:** One pipeline entrypoint plus one new fail-closed gate, both
  governing the existing post-test sequence — no new checks are invented, only ordering
  and enforcement of steps Claude already performs manually.
- **Failure boundary:** The ref-resolution fix this pipeline depends on is C33A
  (already committed). Dashboard schema, telemetry schema, and notify email format are
  unchanged.
- **Budget rationale:** 2 primary files (`finalize_commit.py` new,
  `pre_commit_check.py` edit), 3 changed files total, one combined verification command.
  `hooks/agent-config.json` already lists `hooks/finalize_commit.py`,
  `hooks/tests/test_finalize_commit.py`, and `.context/finalize/` under Claude's domain
  (added during the C33A/C33B replan, ahead of this commit, to avoid a
  chicken-and-egg `file_ownership` validation failure) — no edit needed here.

---

## Background

C33's notify-email step (CLAUDE.md step 11/12,
`NOTIFY_WHAT=... NOTIFY_WHY=... python hooks/notify_agent_done.py --write-flag`) was
skipped entirely — nothing mechanically required it to run. Separately, C33A fixed
`verify_constraints.py`'s ref resolution, but nothing mechanically requires it to be run
with the corrected ref before a commit lands. Both gaps are closed the same way: a
single pipeline that runs every required step in order and a commit-time gate that
proves it ran.

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
bootstrap_exception:
  reason: >
    The new fail-closed finalize-marker gate (pre_commit_check.py) broke an
    existing happy-path test in hooks/tests/test_pre_commit_check.py, which
    required a 7-line .context/finalize/C50.json fixture to keep passing.
    That 4th file plus the new pipeline module (hooks/finalize_commit.py) and
    its full ordering/e2e test suite (hooks/tests/test_finalize_commit.py)
    bring the total diff to ~480 lines.
  max_estimated_diff_lines: 500
```

---

## Context

```yaml
primary_files:
  - hooks/finalize_commit.py
  - hooks/pre_commit_check.py
initial_context:
  - hooks/verify_constraints.py
  - hooks/notify_agent_done.py
  - hooks/pre_commit_check.py
  - hooks/agent-config.json
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/finalize_commit.py` | new | Run verify_constraints -> conditional dashboard render -> notify-flag write -> finalize marker, in fixed order |
| `hooks/pre_commit_check.py` | edit | Fail-closed: block a primary commit (`Commit #NN` + execution marker) unless `.context/finalize/CNN.json` exists and matches |
| `hooks/tests/test_finalize_commit.py` | new | Pipeline ordering/failure tests and pre-commit gate tests |
| `hooks/tests/test_pre_commit_check.py` | edit | Add a `.context/finalize/C50.json` fixture to the existing Claude-direct happy-path test, which the new finalize-marker gate now requires |

---

## Contract

### `hooks/finalize_commit.py`

CLI: `python hooks/finalize_commit.py --commit NN --agent OWNER --execution
{claude-direct,delegated} [--tokens N] [--render-dashboard] --notify-what "..."
--notify-why "..."`

Fixed order, stopping at the first failure:

1. **Verify constraints** — call `verify_constraints.main()`-equivalent (import and
   invoke, not persisted twice) with `--commit NN --agent OWNER --execution EXEC`
   (ref auto-resolved per C33A; `--no-persist` is never passed here, so
   `CONSTRAINT_LOG.md`/`CONTEXT_METRICS.json` are written on success). If any of the
   five checks fail, stop — do not render, notify, or write the marker.
2. **Conditional dashboard render** — render `constraint-dashboard.html` only if
   `--render-dashboard` was passed or `int(NN's numeric prefix) % 5 == 0` (the existing
   five-commit Viktor wave cadence).
3. **Write notify flag** — call `notify_agent_done.write_pending_notify(what, why,
   num=NN, agent=OWNER)` (auto-detects name from `commit-protocol.md` as it does today).
4. **Write finalize marker** — on success of steps 1-3, write
   `.context/finalize/C<NN>.json`:
   ```json
   {"commit": "NN", "agent": "OWNER", "execution": "EXEC",
    "checks_passed": true, "timestamp": "<ISO8601>"}
   ```
5. **Print one structured JSON summary** to stdout:
   ```json
   {"commit": "NN", "status": "ready"|"blocked",
    "checks": {"spec_validation": "...", "context_block": "...",
               "forbidden_paths": "...", "phase_budget": "...", "actual_scope": "..."},
    "dashboard_rendered": true|false, "notify_written": true|false,
    "marker_written": true|false}
   ```

On any check failure: print the same JSON with `status: "blocked"`, `notify_written:
false`, `marker_written: false`, and exit nonzero. Never writes a stale or partial
marker — an existing marker for `NN` is overwritten only on a fresh full success.

### `hooks/pre_commit_check.py`

Add a check that runs alongside the existing domain-boundary / message-format checks:

- Parse the commit message (via the existing `get_commit_message()` and
  `planned_files_for_commit()`'s `Commit #NN` regex). If the message does **not**
  contain both a `Commit #0*NN` line and one of `Execution: Claude-direct` /
  `Co-Authored-By:` (i.e. it is a chore/doc-sweep/state commit, or has neither marker),
  skip this check entirely — exempt.
- Otherwise, require `.context/finalize/C<NN>.json` (zero-padded same as the resolved
  `commit_id`) to exist, be valid JSON, and have `"commit" == NN`, `"agent" ==
  <co-authored-by agent or owner>`, and `"checks_passed" == true`. Mismatched
  `commit`/`agent` fields fail the same as a missing file.
- On failure, block with: `"Run hooks/finalize_commit.py --commit NN --agent OWNER
  --execution EXEC ... before committing (no fresh finalize marker found)."`

### `hooks/agent-config.json` (already done, no edit in this commit)

`hooks/finalize_commit.py`, `hooks/tests/test_finalize_commit.py`, and
`.context/finalize/` are already listed under the `claude@anthropic.com` entry's
`domains` list (added during the C33A/C33B replan), so `pre_commit_check.py`'s
domain-boundary check accepts these paths when this commit lands.

---

## Environment Prerequisites

- Run from the repository root.
- C33A is committed (provides the corrected ref-resolution used by step 1).
- No Docker or application services required.

---

## Verification Command

```powershell
python -m pytest hooks/tests/test_finalize_commit.py -q
```

---

## Focused Tests

- `finalize_commit.py` runs verify -> render (skipped, not a 5th commit) -> notify-flag
  -> marker, in that order, for a passing claude-direct commit; marker file matches the
  documented schema.
- A failing `verify_constraints` check stops the pipeline before dashboard render,
  notify-flag write, or marker write; exit code is nonzero.
- `--render-dashboard` forces the render step even when `NN % 5 != 0`.
- `pre_commit_check.py` blocks a staged primary commit (`Commit #NN` + `Execution:
  Claude-direct`) when `.context/finalize/CNN.json` is missing.
- `pre_commit_check.py` allows the same commit once a matching marker exists.
- `pre_commit_check.py` exempts a `chore(state): advance state after C-NN` commit
  (no `Commit #NN` + execution marker pair) regardless of `.context/finalize/` state.
- A marker whose `"commit"` or `"agent"` field doesn't match the staged commit blocks,
  same as a missing marker.

---

## Done When

- [ ] `hooks/finalize_commit.py` exists and runs the four steps in the documented fixed
      order, stopping at the first failure.
- [ ] `pre_commit_check.py` fails closed on primary commits without a fresh, matching
      finalize marker, and is exempt for chore/doc-sweep/state commits.
- [ ] `hooks/agent-config.json` lists `hooks/finalize_commit.py` and
      `.context/finalize/` under Claude's domain.
- [ ] `python -m pytest hooks/tests/test_finalize_commit.py -q` passes.
- [ ] No files under `backend/` or `frontend/` changed.

---

## Developer Test Checkpoint

**Next milestone:** C37.

---

## Not In This Commit

- Changes to the notify email format, dashboard schema, or telemetry schema.
- Adding `hooks/finalize_commit.py` to CLAUDE.md's "Files You Own" list — done in the
  following chore/doc-sweep commit alongside the rest of the protocol-file updates.
- Orchestrator token tracking for Claude-direct commits (OI-03 follow-up) — separate,
  unscheduled future work.

---

## Return Contract

Claude-direct: report the diff, the test run output, and a worked example showing the
pipeline blocking a commit without a marker, then succeeding once
`finalize_commit.py` has run.
