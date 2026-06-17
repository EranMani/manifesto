# CLAUDE.md - Manifesto Operating Contract

Claude is the orchestrator and default implementor. Execute only an approved commit
specification. Eran is the final authority.

## Boot

1. Read `project-state.json` keys `tldr`, `next_commit`, `next_commit_name`, and blockers.
2. Read the active `commit-specs/commit-NN.md`.
3. Read `DECISIONS.md` only when the state or spec references an unresolved decision.
4. Use `ORCHESTRATION.md` for detailed process explanations, not as routine boot context.

Do not scan the repository at boot.

## Approval And Routing

- Claude-direct is the default.
- Delegate only for unresolved specialist uncertainty, independent risk control, or a
  bounded specialist unit whose value exceeds invocation overhead.
- Workflow changes, mechanical wiring, narrow repairs, known edits, and straightforward
  tests remain Claude-direct.
- Before implementation, run the matching preflight and show Eran the compact card.
- Wait for explicit approval. Approval authorizes only the listed commit and files.
- After Eran approves a READY preflight, routine execution choices are pre-approved:
  delegation start, telemetry persistence, focused verification, constraint checks,
  finalize/commit, chore state sweep, and dashboard/protocol/state updates required by
  the approved commit. Do not ask again for each routine step.
- Ask Eran again only for a real decision: new files outside the spec, changed behavior,
  a failed test requiring implementation judgment, a non-routine override, destructive
  git operation, or a split/replan.

Direct preflight:

```powershell
python hooks/preflight_commit.py --direct --commit NN --agent OWNER
```

Delegated preflight:

```powershell
python hooks/preflight_commit.py --commit NN --agent OWNER
```

The card must state goal, files, owner, executor, verification, risks, and delegation
justification. Do not dump the full specification when the compact card is ready.

## Execution

### Claude Direct

The `direct_execution_lifecycle.py` hook prepares `.context/direct/CNN.md` and starts
full execution telemetry before the first implementation tool event. Follow its file
order. Edit only files in the approved spec.

### Delegated

Run:

```powershell
python hooks/prepare_agent_delegation.py --commit NN --agent AGENT
```

Pass the generated brief to the named agent. Agents read selected files first, avoid
directory scans, and expand context only for a missing contract, unresolved symbol,
failing test, or contradictory evidence.

After the agent returns:

1. Persist its structured telemetry report.
2. Start or confirm Claude's review-only telemetry scope.
3. Inspect the diff and run the specified verification.
4. If Claude must implement or repair work, record both the delegated agent and Claude
   in telemetry and dashboard execution history.

Never label a delegated commit as "not delegated" merely because Claude finished it.

## Live Budgets

`hooks/claude_budget.py` records these top-level Claude limits:

| Scope | Warn | Stop |
|---|---:|---:|
| Direct | 25 actions / 25 turns / 100K active tokens | 40 / 40 / 150K |
| Delegated review | 15 actions / 20 turns / 75K active tokens | 20 / 25 / 100K |

Active tokens are input + output + cache creation. Cache-read tokens remain visible but
do not trigger a stop. For orchestration actions (preflight, delegation, reads/searches,
verification, finalization, state sweeps, and agent invocation), a hard stop is advisory:
continue and keep the overage visible. Do not ask Eran for routine orchestration
overrides.

For Claude product writes after a hard stop, split the work or obtain Eran's explicit
approval for a bounded override:

```powershell
python hooks/claude_budget.py --authorize-override "Eran approved: REASON"
```

Do not authorize a product-write override without Eran's approval.

Delegated agents retain the limits in their generated brief and `tool_cap_*` hooks.

## Verification And Commit

1. Run the spec's focused verification command.
2. Run constraint verification:

```powershell
python hooks/verify_constraints.py --commit NN --agent OWNER --execution claude-direct
```

For delegated execution, use `--execution delegated --tokens N`.

3. Run `python hooks/finalize_commit.py --commit NN` before the primary commit.
4. Inspect `git diff --check` and the staged diff.
5. Commit only after all required checks pass.

Direct commit message:

```text
type(scope): description

Commit #NN
Execution: Claude-direct

Co-Authored-By: Claude <claude@anthropic.com>
```

Delegated commits credit the actual implementing agent and omit
`Execution: Claude-direct`. Hooks advance protocol state after a successful commit.

Never amend or rewrite history unless Eran explicitly asks. Never revert unrelated user
changes. A blocking gate finding becomes a new commit; there are no gate-fix passes.

## Scope And Ownership

- The active spec's `Files To Modify Or Add` table is the exact write boundary.
- Claude-direct authority is commit-specific, not broad domain ownership.
- Respect `AGENTS.md` domain boundaries and cross-domain finding format.
- Do not perform unrelated cleanup.
- If the task cannot fit the approved file, diff, action, or token budget, stop and
  return `SPLIT_REQUIRED` with completed work, remaining work, and a proposed split.

Claude owns orchestration documents, commit specs, `.claude/settings.json`, and the
narrow workflow hooks explicitly listed under Claude in `hooks/agent-config.json`.

## Quality Gates

Use the trigger matrix in `AGENTS.md`.

- Viktor: batch review every fifth commit.
- Sage: security-sensitive changes.
- Mira: user-facing behavior.
- Blocking findings become the next commit.

All agent-to-agent communication routes through Claude.

## Return Contract

Every implementor starts with:

```markdown
## Human Summary
**What I completed:** ...
**What changed:** ...
**What went wrong:** None.
**What remains:** None.
**Recommended next commit:** ...
**Developer attention:** None.
```

Delegated implementors then return:

```json
{
  "tool_calls": 0,
  "read_paths": [],
  "write_paths": [],
  "searches": [],
  "commands": [],
  "expansions": []
}
```

`tool_calls` is required. Use `null` for path arrays only when detail is unavailable.

## Non-Negotiables

1. One approved commit at a time.
2. No implementation before explicit approval.
3. No secrets, fabricated telemetry, or hidden overrides.
4. No agent may commit.
5. No direct agent-to-agent contact.
6. No repository-wide scans when targeted reads suffice.
7. No claiming tests passed unless they were run.
8. No changing execution attribution after the fact.
9. Stop on scope ambiguity rather than silently broadening work.
10. Keep founder-facing summaries plain and outcome-oriented.

Detailed rationale, rollback, replanning, context selection, slash commands, and examples
live in `ORCHESTRATION.md`.
