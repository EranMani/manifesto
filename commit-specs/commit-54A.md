# Commit 54A - `powershell-budget-closeout-fix` - Claude

**Phase:** Governance repair
**Owner:** claude
**Depends on:** C53A
**Estimated diff lines:** 30
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
`allowed_after_stop()` and `is_closeout_action()` treat PowerShell tool calls identically to Bash for control commands and override authorization.

## Semantic Fit Review
- **Atomic outcome:** Budget gate unblocks when closeout commands run via PowerShell.
- **Failure boundary:** Non-closeout PowerShell edits remain blocked.
- **Budget rationale:** One-line fix + two regression tests; fits direct execution trivially.

## Execution Budget
```yaml
execution_budget:
  max_primary_files: 1
  max_changed_files: 4
  max_context_files: 2
  max_context_chars: 8000
  max_estimated_diff_lines: 200
  max_agent_invocations: 0
  max_tool_calls: 10
  max_expansions: 0
  max_implementor_tokens: 0
```

## Context
```yaml
primary_files:
  - hooks/claude_budget.py
  - hooks/tests/test_claude_budget.py
initial_context:
  - hooks/claude_budget.py
  - hooks/tests/test_claude_budget.py
forbidden:
  - frontend/
  - backend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `hooks/claude_budget.py` | edit | Extend `allowed_after_stop()` to accept PowerShell alongside Bash. |
| `hooks/tests/test_claude_budget.py` | edit | Add regression tests for PowerShell closeout commands and override authorization. |
| `commit-specs/commit-54A.md` | add | This spec file. |
| `commit-protocol.md` | edit | Register C54A in the commit index. |

## Contract
`allowed_after_stop(event)` accepts `tool_name` of `"Bash"` or `"PowerShell"` and checks the `command` field against `CONTROL_COMMANDS`. All other behaviour is unchanged. Two new tests cover: (1) a PowerShell finalize_commit.py command is allowed after stop; (2) a PowerShell `--authorize-override` command is allowed after stop.

## Environment Prerequisites
- C53A budget override mechanism is in place.

## Verification Command
```powershell
python -m pytest hooks/tests/test_claude_budget.py -q
```

## Focused Tests
- PowerShell closeout command passes `allowed_after_stop`.
- PowerShell `--authorize-override` passes `allowed_after_stop`.

## Done When
- [ ] All existing and new `test_claude_budget.py` tests pass.
- [ ] Scope within budget.

## Developer Test Checkpoint

**Next milestone:** C56 (`unified-assistant-api`) is the next backend milestone after C54 resumes.

## Not In This Commit
- Any change outside `hooks/claude_budget.py` and its test file.

## Return Contract
Begin with the required Human Summary. No structured telemetry needed (Claude-direct).
