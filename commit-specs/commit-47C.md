# Commit 47C - `telemetry-finalize-idempotency` - Claude

**Phase:** Logistics evidence (governance interrupt)
**Owner:** claude
**Depends on:** C47B
**Executor:** recovery (Codex-derived)
**Estimated diff lines:** 35
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior

`finalize_commit.py` accepts a valid, already-completed matching telemetry scope
as an idempotent close instead of requiring an active running scope.

## Semantic Fit Review

- **Atomic outcome:** One finalization retry behavior becomes idempotent.
- **Failure boundary:** Telemetry activation and token calculation are unchanged.
- **Budget rationale:** One source file and its focused test file.

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 1
  max_changed_files: 2
  max_context_files: 2
  max_context_chars: 8000
  max_estimated_diff_lines: 80
  max_agent_invocations: 0
  max_tool_calls: 10
  max_expansions: 1
  max_implementor_tokens: 0
```

## Context

```yaml
primary_files:
  - hooks/finalize_commit.py
initial_context:
  - hooks/finalize_commit.py
  - hooks/tests/test_finalize_commit.py
forbidden:
  - backend/
  - frontend/
```

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/finalize_commit.py` | edit | Accept an already-completed matching telemetry record as a successful close. |
| `hooks/tests/test_finalize_commit.py` | edit | Cover idempotent completed-scope handling. |

## Contract

Finalization closes a matching running scope when present. If the permanent
matching scope is already completed, the close step succeeds without changing
or replacing telemetry.

## Verification Command

```powershell
python -m pytest hooks/tests/test_finalize_commit.py -q
```

## Focused Tests

- A completed matching permanent scope is accepted as already closed.
- A missing or mismatched scope still blocks finalization.

## Done When

- [x] Completed matching telemetry is accepted without mutation.
- [x] Focused finalizer tests pass.

## Not In This Commit

- C48 application changes.
- Telemetry activation and initialization guards, which land in C47B.

## Environment Prerequisites

- Run from the repository root. No application services required.

## Developer Test Checkpoint

**Next milestone:** C48 resumes immediately after C47C.

## Return Contract

Report the focused test result and confirm C48 files remain unstaged.
