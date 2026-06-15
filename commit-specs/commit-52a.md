# Commit 52A - `claude-budget-and-cache-reduction` - Claude

**Phase:** Phase 2 workflow governance
**Owner:** claude
**Depends on:** C52
**Status:** implemented retrospectively in `796ef48`
**Estimated diff lines:** 980
**Primary behavior count:** 3
**Developer test milestone:** no

---

## Governance Note

This specification was written after implementation. That violated the repository rule
that every commit is specified and listed in `commit-protocol.md` before code is written.
The implementation must not be represented as having passed normal preflight governance.
Eran identified the omission immediately after commit `796ef48`.

The work also combined the planned telemetry, enforcement, and instruction-reduction
steps instead of landing them as separate C52A-C52C commits. This retrospective record
preserves the true history rather than rewriting or fabricating prior approval evidence.

## Implemented Behaviors

1. Claude-direct and delegated-review scopes receive live action, turn, and active-token
   warning and stop thresholds.
2. Hard stops block additional research or implementation while allowing deterministic
   closeout commands and an explicitly approved one-use override.
3. `CLAUDE.md` is reduced from 34,798 bytes to 6,064 bytes, with a regression test.

Cache-read tokens remain observable but do not count toward active-token stops.

## Files Changed

| File | Purpose |
|---|---|
| `.claude/settings.json` | Register the live Claude budget hook |
| `CLAUDE.md` | Provide a lean always-loaded operating contract |
| `CLAUDE_BUDGET_AND_CACHE_REDUCTION_ROADMAP.md` | Record thresholds and rollout intent |
| `hooks/agent-config.json` | Register Claude ownership |
| `hooks/claude_budget.py` | Measure and enforce direct/review budgets |
| `hooks/tests/test_claude_budget.py` | Test enforcement behavior |
| `hooks/tests/test_context_telemetry.py` | Align a stale dashboard assertion |
| `hooks/tests/test_instruction_budget.py` | Guard instruction size and controls |

## Budget Contract

| Scope | Warn | Stop |
|---|---:|---:|
| Claude direct | 25 actions / 25 turns / 100K active tokens | 40 / 40 / 150K |
| Delegated review | 15 actions / 20 turns / 75K active tokens | 20 / 25 / 100K |

Active tokens are `input + output + cache_creation_input`. Cache reads are reported
separately. A hard stop permits deterministic closeout commands until Eran approves a
one-use override.

## Verification Evidence

```powershell
pytest -p no:cacheprovider hooks/tests/test_claude_budget.py hooks/tests/test_instruction_budget.py hooks/tests/test_context_telemetry.py -q
```

Result recorded at implementation: `28 passed`.

The complete hook suite recorded `285 passed` and 7 unrelated existing failures. The
suite was therefore not fully green.

## Done When

- [x] Live budget state is persisted.
- [x] Direct and review scopes have separate limits.
- [x] Cache reads are excluded from active-token enforcement.
- [x] Hard stops mechanically block non-closeout tools.
- [x] A one-use override records its reason.
- [x] Always-loaded instructions are reduced by at least 40%.
- [x] Focused tests pass.
- [x] The retrospective governance omission is recorded honestly.

## Not In This Commit

- Dashboard presentation of live budget state.
- Repair of unrelated full-suite failures.
- Rewriting history to imply this specification existed before `796ef48`.
