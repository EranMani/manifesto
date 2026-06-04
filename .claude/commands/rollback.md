# /rollback — Rollback Protocol

Triggered when: a committed change has caused a regression, a commit was made in error,
or the Team Lead decides a completed step must be undone.

---

## Step 1 — Identify the target commit

Ask the Team Lead: "Which commit do you want to roll back? State the commit number and name."

Do not proceed without an explicit answer. Do not assume.

---

## Step 2 — Assess blast radius

Read `project-state.json` and `commit-protocol.md`. For the target commit [N]:

Answer the following:

| Question | Answer |
|---|---|
| Which agents' work depended on commit [N]? | [list] |
| Which commits after [N] are now invalidated? | [list] |
| Which open handoffs referenced commit [N]? | [list] |
| Are any of the invalidated commits already committed? | yes / no |

Surface the full blast radius to the Team Lead before doing anything.
Format:

```
Rollback blast radius — Commit [N] `[name]`

Directly invalidated commits: [N+1], [N+2] (if already committed)
Agents affected: [list]
Open handoffs that referenced this commit: [list]
Files that will be reverted: [list from git show --name-only]

This rollback will affect [X] committed steps and [Y] pending steps.
```

---

## Step 3 — Team Lead confirms

Do not execute any git command until the Team Lead says: "Confirmed — roll back commit [N]."

---

## Step 4 — Execute the rollback

```bash
git revert [commit-hash] --no-commit   # stage the revert without committing yet
git diff --staged                       # show Team Lead what will be reverted
```

Surface the diff to the Team Lead. Wait for final confirmation before committing the revert.

Once confirmed:
```bash
git commit -m "revert: roll back commit [N] [name]

Reason: [Team Lead's stated reason]
Reverts: [original commit hash]
Affected agents notified: [list]

Co-Authored-By: Claude <claude@anthropic.com>"
```

---

## Step 5 — Update project state

After the revert commit lands:

1. **`commit-protocol.md`** — Change the reverted commit's status back to `pending`. Add a note:
   ```
   | [N] | [name] | [agent] | ⏪ reverted · [date] · reason: [one sentence] |
   ```

2. **`project-state.json`** — Update:
   - Remove the commit from `commits_done`
   - Add it back to `commits_pending` at the correct position
   - Add entry to `rollback_history`
   - Remove or flag any open handoffs that were based on the reverted work

3. **Affected agent worklogs** — Append a rollback notice to each affected agent's worklog:
   ```markdown
   ## ⏪ Rollback Notice — [date]

   Commit [N] `[name]` has been reverted.
   Reason: [Team Lead's stated reason]
   Impact on your work: [what this means for the agent specifically]
   What to do next: [wait for re-assignment / specific action required]
   ```

---

## Step 6 — Re-sequence the commit protocol

If commits after [N] were also reverted, re-sequence `commit-protocol.md`:

- Mark all invalidated commits as `⏪ reverted · [date]`
- Confirm with Team Lead whether these commits should be re-done in the same order
  or whether the plan itself needs to change
- If the plan changes → run `/replan` after rollback is complete

---

## Step 7 — Brief the Team Lead

```
✅ Rollback complete.

Reverted: Commit [N] `[name]`
Revert commit: [hash]
Status updated in: commit-protocol.md, project-state.json
Agents notified: [list]

Next step: Commit [N] `[name]` is back to pending — assigned to [agent].
[If plan change needed]: Recommend running /replan before re-starting.
Shall I proceed with re-running Commit [N]?
```

---

## Rollback Non-Negotiables

- Never force-push. Rollbacks are revert commits, not history rewrites.
- Never rollback without Team Lead confirmation of the blast radius.
- Never assume a rollback is "small" — always assess all downstream commits.
- Always notify affected agents. A rollback that silently invalidates a teammate's
  assumptions is worse than the original bug.
