# Commit 33A - `verify-constraints-ref-fix` - Claude

**Phase:** Workflow Redesign - Stop the Bleeding
**Owner:** claude
**Depends on:** C33
**Execution mode:** Claude-direct
**Estimated diff lines:** 140
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

`hooks/verify_constraints.py` resolves the correct git ref for a commit's actual-scope
check on its own, instead of silently defaulting to `HEAD` when `--ref` is omitted and
`--worktree` is not set.

---

## Semantic Fit Review

- **Atomic outcome:** One function (`resolve_primary_commit_ref`) plus one call-site
  change in `check_actual_scope`/`main`.
- **Failure boundary:** The finalize-commit pipeline that calls this corrected logic is
  C33B. This commit only fixes ref resolution; it does not add the pipeline, the notify
  step, or the pre-commit gate.
- **Budget rationale:** 2 exact changed file(s) (implementation + its test file), no new
  context files beyond the file under repair, one focused verification command.

---

## Background

While closing out C33, re-running
`python hooks/verify_constraints.py --commit 33 --agent rex --execution claude-direct --render-dashboard`
*after* the C33 doc-sweep/chore commit had already landed caused `check_actual_scope` to
diff `HEAD` (the chore commit) against C33's spec. The chore commit's files
(`CONSTRAINT_LOG.md`, `CONTEXT_METRICS.json`, `TOKEN_RECORDS.md`, `commit-protocol.md`,
`project-state.json`) were reported as "unplanned files" for C33, producing a false
`actual_scope: FAIL` that was persisted into `CONTEXT_METRICS.json`. Recovery required
`git checkout -- CONTEXT_METRICS.json` and a manual dashboard re-render.

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
  - hooks/verify_constraints.py
initial_context:
  - hooks/verify_constraints.py
  - hooks/tests/test_verify_constraints.py
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/verify_constraints.py` | edit | Resolve the correct primary-commit ref for `--commit NN` instead of defaulting to `HEAD` |
| `hooks/tests/test_verify_constraints.py` | edit | Regress ref resolution after later commits have landed |
| `commit-specs/commit-33A.md` | edit | Normalize `**Owner:**` to `claude` (was a verbose parenthetical form that broke `preflight_commit.py`'s owner-path lookup) |
| `commit-specs/commit-33B.md` | edit | Same `**Owner:**` normalization, for consistency and to unblock C33B's own preflight |

---

## Contract

Add `resolve_primary_commit_ref(commit_num: str, agent: str, root: Path = REPO_ROOT) ->
str`:

- Search `git log --format="%H%x00%B%x03"` (or equivalent) for the most recent commit
  whose body contains both a `Commit #0*<commit_num>` line (matching the same pattern
  `pre_commit_check.py.planned_files_for_commit` already uses) and either
  `Execution: Claude-direct` or a `Co-Authored-By:` trailer.
- Return that commit's full SHA if found.
- If no matching commit exists, return `"HEAD"` and emit a non-fatal warning string
  (surfaced in both human and `--json` output as `"ref_resolution": "fallback to HEAD -
  no commit matching 'Commit #NN' found"`).

In `main()`:

- If `--worktree` is set, behavior is unchanged (diff against working tree).
- If `--ref` is explicitly passed on the command line, it is honored as-is (no
  auto-resolution) — preserves existing callers that pass an explicit ref.
- If `--ref` is **not** passed (still its default), call
  `resolve_primary_commit_ref(args.commit, args.agent)` and use the result as the
  effective ref for both `git_files_changed()` and `check_actual_scope()`'s `git show`
  call.

Argparse change: `--ref` default becomes `None` (was `"HEAD"`); resolve to `"HEAD"` only
through `resolve_primary_commit_ref`'s fallback, so the "no `--ref` passed" and "`--ref
HEAD` passed explicitly" cases remain distinguishable.

No change to `check_spec_validation`, phase-budget checks, dashboard rendering, or
persistence behavior — only which ref is diffed.

---

## Environment Prerequisites

- Run from the repository root.
- Git history must contain C33's commit (this repo already does).
- No Docker or application services required.

---

## Verification Command

```powershell
python -m pytest hooks/tests/test_verify_constraints.py -q
```

---

## Focused Tests

- `resolve_primary_commit_ref` finds C33's commit SHA even when a later chore commit is
  `HEAD`.
- An explicit `--ref <sha>` overrides auto-resolution.
- No matching commit for a given number falls back to `"HEAD"` and reports
  `ref_resolution` as a warning, not a silent pass-through.
- Regression: re-running `--commit 33 --agent rex --execution claude-direct
  --no-persist` after a synthetic chore commit on top reports `actual_scope: ok` (not
  the C33 corruption failure mode).

---

## Done When

- [ ] `resolve_primary_commit_ref` is implemented and used by default when `--ref` is
      omitted and `--worktree` is not set.
- [ ] Explicit `--ref` and `--worktree` behavior is unchanged.
- [ ] `python -m pytest hooks/tests/test_verify_constraints.py -q` passes.
- [ ] No files under `backend/` or `frontend/` changed.

---

## Developer Test Checkpoint

**Next milestone:** C37.

---

## Not In This Commit

- The `finalize_commit.py` pipeline, notify-flag automation, and pre-commit finalize
  gate — C33B.
- Any change to `CONTEXT_METRICS.json`, `CONSTRAINT_LOG.md`, or
  `constraint-dashboard.html` content/schema.
- `hooks/agent-config.json` changes.

---

## Return Contract

Claude-direct: report the diff, the test run output, and confirm the regression
scenario (chore commit on top of the target commit) now resolves correctly.
