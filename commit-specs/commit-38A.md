# Commit 38A - `orchestrator-telemetry-marker-gate` - Claude

**Phase:** Workflow Redesign - Stop the Bleeding
**Owner:** claude
**Depends on:** C38
**Execution mode:** Claude-direct
**Estimated diff lines:** 120
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

`pre_commit_check.py` fails closed on a primary commit unless a completed
`.context/telemetry/C<NN>-orchestrator.json` scope (steps 5b/7c) exists and matches.

---

## Semantic Fit Review

- **Atomic outcome:** One new gate, mirroring the existing `check_finalize_marker()`
  pattern, governing a step Claude is already required to perform (CLAUDE.md steps
  5b/7c, Rule 14) but has twice skipped (C38 regression vs. C36/C37).
- **Failure boundary:** No change to `context_telemetry.py` itself — `.context/telemetry/CNN-orchestrator.json`
  is already written correctly by `--start-orchestrator`/`--stop-orchestrator` when run.
  This commit only adds the commit-time check that those steps ran.
- **Budget rationale:** 1 primary file (`hooks/pre_commit_check.py` edit), 2 changed
  files total (test file edit), one focused verification command.

---

## Background

CLAUDE.md Rule 14 and steps 5b/7c require every commit (Claude-direct or delegated) to
open and close an orchestrator telemetry scope via `context_telemetry.py
--start-orchestrator CNN` / `--stop-orchestrator CNN`. C36 and C37 did this correctly
(`.context/telemetry/C36-orchestrator.json`, `C37-orchestrator.json` both exist with
`status: "completed"`). C38 skipped both steps — no `C38-orchestrator.json` was
written, and `CONTEXT_METRICS.json`'s C38 record shows `orchestrator.status:
"unavailable"`, a silent data-quality regression (logged as a −2 B4/C3 deduction in
COMMIT_HEALTH_RUBRIC.md). Following the precedent of C33B/D39 (a prose-only fix for a
missed step did not stick — OI-13/OI-14 for the `cd` pattern recurred 5 times), this
commit converts the missed step into a fail-closed gate, the same way
`check_finalize_marker()` did for the notify/finalize step.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 1
  max_changed_files: 2
  max_context_files: 4
  max_context_chars: 12000
  max_estimated_diff_lines: 200
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

> **Amended post-implementation (D43, Eran-approved):** `max_estimated_diff_lines`
> raised from 150 to 200. The actual diff (43 lines in `pre_commit_check.py` + 149
> lines in `test_pre_commit_check.py`, totaling 192) covers all 6 required Focused
> Tests plus the `C50-orchestrator.json` happy-path fixture; trimming would reduce
> required test coverage.

---

## Context

```yaml
primary_files:
  - hooks/pre_commit_check.py
initial_context:
  - hooks/pre_commit_check.py
  - hooks/tests/test_pre_commit_check.py
  - hooks/context_telemetry.py
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/pre_commit_check.py` | edit | Add `check_orchestrator_telemetry_marker()`, called alongside `check_finalize_marker()` |
| `hooks/tests/test_pre_commit_check.py` | edit | Add tests for the new gate; add a `C50-orchestrator.json` fixture to the existing happy-path test |

---

## Contract

### `hooks/pre_commit_check.py`

Add `check_orchestrator_telemetry_marker(msg, config)`, mirroring
`check_finalize_marker()`'s structure:

- Parse the commit message for `Commit #0*NN` and an execution marker
  (`Execution: Claude-direct` or `Co-Authored-By:`), exactly as `check_finalize_marker`
  does. If either is absent (chore/doc-sweep/state commits), return `[]` — exempt.
- Otherwise compute `commit_key = "C" + commit_id.zfill(2).upper()` (same normalization
  as `check_finalize_marker`, e.g. `"38"` -> `"C38"`, `"33b"` -> `"C33B"`) and
  `marker_path = .context/telemetry/<commit_key>-orchestrator.json`.
- Require: the file exists, is valid JSON, `scope["commit"] == commit_key`, and
  `scope["status"] == "completed"`. Any failure (missing file, parse error, mismatched
  commit, status not `"completed"`) returns one error:
  ```
  Run hooks/context_telemetry.py --start-orchestrator <commit_key> before step 6a
  inspection and --stop-orchestrator <commit_key> after /verify-commit passes (no
  completed orchestrator telemetry scope found).
  ```
- Call this alongside `check_finalize_marker(msg, config)` in the existing error chain
  (same call site, same `errors.extend(...)` pattern).

No change to `context_telemetry.py`, `.context/finalize/`, or `hooks/agent-config.json`
domains — `.context/telemetry/` is gitignored and read-only from this hook's
perspective; no new tracked path is introduced.

---

## Environment Prerequisites

- Run from the repository root. No Docker or application services required.

---

## Verification Command

```powershell
python -m pytest hooks/tests/test_pre_commit_check.py -q
```

---

## Focused Tests

- `pre_commit_check.py` blocks a staged primary commit (`Commit #NN` + `Execution:
  Claude-direct`) when `.context/telemetry/CNN-orchestrator.json` is missing.
- `pre_commit_check.py` allows the same commit once a `status: "completed"` scope file
  with a matching `commit` field exists.
- A scope file with `status: "running"` (stop-orchestrator never ran) blocks, same as
  missing.
- A scope file whose `commit` field doesn't match the staged commit blocks, same as
  missing.
- `pre_commit_check.py` exempts a `chore(state): advance state after C-NN` commit (no
  `Commit #NN` + execution marker pair) regardless of telemetry scope state.
- The existing `test_valid_claude_direct_commit_passes_normally` happy-path test still
  passes once it is given a matching `C50-orchestrator.json` fixture (mirrors the
  `C50.json` finalize-marker fixture added in C33B).

---

## Done When

- [ ] `check_orchestrator_telemetry_marker()` exists and is wired into the error chain
      alongside `check_finalize_marker()`.
- [ ] A primary commit without a completed `.context/telemetry/CNN-orchestrator.json`
      is blocked with the documented message.
- [ ] A primary commit with a completed, matching scope file passes.
- [ ] chore/doc-sweep/state commits remain exempt.
- [ ] `python -m pytest hooks/tests/test_pre_commit_check.py -q` passes.
- [ ] No files under `backend/` or `frontend/` changed.

---

## Developer Test Checkpoint

**Next milestone:** C49.

---

## Not In This Commit

- No change to `context_telemetry.py`'s scope-writing logic itself (already correct).
- No retroactive fix for C38's own missing telemetry record.
- C39 (`policy-vector-candidates`, nova) — unaffected, proceeds after this commit.

---

## Return Contract

Claude-direct: report the diff, the test run output, and a worked example showing the
gate blocking a commit without a scope file, then passing once
`context_telemetry.py --start-orchestrator`/`--stop-orchestrator` has been run.
