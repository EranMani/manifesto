# Commit 47B - `telemetry-lifecycle-overwrite-fix` - Claude

**Phase:** Logistics evidence (governance interrupt)
**Owner:** claude
**Depends on:** C47
**Executor:** recovery (Codex-derived) — see Background
**Estimated diff lines:** 140
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

`hooks/direct_execution_lifecycle.py`'s PreToolUse hook no longer silently
re-initializes (and thereby overwrites) a `running` Claude-direct execution
telemetry scope when a later Bash tool call invokes a telemetry/finalize/verify
control script for the same commit. `context_telemetry.py` and
`finalize_commit.py` gain matching guards so a scope can never be silently
replaced or double-finalized.

---

## Semantic Fit Review

- **Atomic outcome:** One lifecycle-hook bug (silent scope overwrite) closed,
  with matching defensive guards in the two collaborating modules.
- **Failure boundary:** No change to the telemetry schema, `finalize_commit.py`'s
  step ordering, or `pre_commit_check.py`'s gates — only the conditions under
  which a scope may be (re)initialized or finalized.
- **Budget rationale:** 3 source files + 3 matching test files, all already
  implemented and passing; expanded `max_changed_files` from the usual 4 to 6
  to keep the fix and its tests in one commit (see Background).

---

## Background

During C48 (`procurement-relationship-evidence`), the Claude-direct execution
scope for C48 (`.context/telemetry/orchestrator-active.json`, `status:
"running"`, `tool_calls: 26`, real `read_paths`/`write_paths`/`commands`) was
successfully closed by `context_telemetry.py --stop-orchestrator 48`. The
subsequent `finalize_commit.py` Bash command included the planned filename
`rag_logistics.py` in notification text. The lifecycle hook misclassified that
control command as implementation, opened a fresh empty scope, and finalization
overwrote the valid completed record with the empty result. It then correctly
failed closed: `"Claude-direct capture is empty; execution scope started too
late"`.

C48's real telemetry was recovered deterministically from the Claude transcript
(see `.context/telemetry/C48-orchestrator.json`'s `recovery` block: scope
boundaries derived from the transcript tool-result at JSONL line 130 through the
byte offset of the `--stop-orchestrator` call, 26 tool calls, 43 assistant
turns, full token totals) — no token telemetry in this commit or in C48's record
is invented.

This commit's code changes (`hooks/direct_execution_lifecycle.py`,
`hooks/context_telemetry.py`, `hooks/finalize_commit.py`, and their three test
files) were produced as part of that same recovery process (Codex-derived), not
authored by Claude in a measured Claude-direct session — hence `Executor:
recovery (Codex-derived)` above, and no `Execution: Claude-direct` marker in the
commit message. Claude's role in landing this commit is the governance work:
this spec, the `commit-protocol.md`/`project-state.json` replan entries, running
the 45-test verification, and the commit itself — captured as a normal
Claude review-telemetry scope (`--start-review` / `--stop-orchestrator`,
`execution_mode: "delegated"`, `scope_kind: "review"`).

C48's implementation files (`backend/app/services/rag_logistics.py`,
`backend/tests/services/test_rag_logistics.py`, `.context/direct/C48.md`)
remain unstaged and unchanged by this commit; C48 resumes immediately after.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 4
  max_context_chars: 12000
  max_estimated_diff_lines: 160
  max_agent_invocations: 0
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 0
```

> Expanded from the usual 4-file / 4-row cap to 6 files (3 source + 3 matching
> test files) because the fix and its regression tests were produced together
> during recovery and splitting them would leave either the guard or its test
> coverage uncommitted. `max_agent_invocations` and `max_implementor_tokens` are
> 0 — no agent was invoked and no implementor token telemetry applies (executor
> is recovery/Codex-derived, not a measured Claude-direct or delegated
> implementor session).

---

## Context

```yaml
primary_files:
  - hooks/direct_execution_lifecycle.py
  - hooks/context_telemetry.py
initial_context:
  - hooks/direct_execution_lifecycle.py
  - hooks/context_telemetry.py
  - hooks/tests/test_direct_execution_lifecycle.py
  - hooks/tests/test_context_telemetry.py
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/direct_execution_lifecycle.py` | edit | Exclude telemetry/finalize/verify control commands from scope-trigger matching; refuse to silently replace an existing scope for the same commit. |
| `hooks/context_telemetry.py` | edit | `initialize_orchestrator_scope` raises instead of overwriting an existing/running scope; `finalize_orchestrator_scope` only finalizes `status == "running"` scopes. |
| `hooks/tests/test_direct_execution_lifecycle.py` | edit | Regression tests for control-command exclusion and refusal to overwrite an existing scope. |
| `hooks/tests/test_context_telemetry.py` | edit | Regression tests for the init-guard and finalize-guard. |

---

## Contract

A Claude-direct execution telemetry scope, once opened with `status: "running"`
for a given commit, is never silently replaced or re-finalized by a later
control-script Bash call for the same commit. `direct_execution_lifecycle.py`
recognizes `hooks/context_telemetry.py`, `hooks/finalize_commit.py`,
`hooks/prepare_claude_direct.py`, and `hooks/verify_constraints.py` invocations
as control commands and never treats them as scope-(re)triggering implementation
tool calls. If any active-file record already exists for the same commit,
`ensure_direct_scope` preserves it and passes the tool through without
reactivation. The lower-level initializer remains the authoritative overwrite
guard.

---

## Environment Prerequisites

- Run from the repository root. No Docker or application services required.

---

## Verification Command

```powershell
python -m pytest hooks/tests/test_direct_execution_lifecycle.py hooks/tests/test_context_telemetry.py -q
```

---

## Focused Tests

- A Bash command invoking `hooks/context_telemetry.py --stop-orchestrator <C>`
  (or `finalize_commit.py`, `prepare_claude_direct.py`, `verify_constraints.py`)
  does not trigger `ensure_direct_scope` to re-initialize a scope.
- `ensure_direct_scope` passes through without reactivation when a completed
  or review scope already exists for the same commit.
- `initialize_orchestrator_scope` raises `ValueError` when a scope for the same
  commit already exists, or when a different commit's scope is `running`.
- `finalize_orchestrator_scope` returns `None` (no-op) for a scope whose status
  is not `running`.
- `finalize_commit.py`'s `step_close_capture` returns success when the matching
  `C<NN>-orchestrator.json` is already `status: "completed"`.

---

## Done When

- [x] `direct_execution_lifecycle.py` excludes control commands and preserves
      existing same-commit scopes without reactivation or tool lockout.
- [x] `context_telemetry.py` guards both initialization and finalization.
- [x] `finalize_commit.py`'s capture-close step is idempotent.
- [x] `python -m pytest hooks/tests/test_direct_execution_lifecycle.py hooks/tests/test_context_telemetry.py hooks/tests/test_finalize_commit.py -q` passes (45/45).
- [x] No files under `backend/` or `frontend/` changed; C48's implementation
      files remain unstaged.

---

## Developer Test Checkpoint

**Next milestone:** C48 resumes immediately (already implemented, pending finalize).

---

## Not In This Commit

- C48 (`procurement-relationship-evidence`) — implementation already complete
  and unstaged; finalizes immediately after this commit lands.
- No retroactive correction of C48's pre-recovery telemetry beyond the
  transcript-derived `recovery` block already present in
  `.context/telemetry/C48-orchestrator.json`.

---

## Return Contract

Claude (review/governance role): report the diff, the 45/45 test run, and
confirm C48's implementation files remain unstaged before and after this
commit lands.
