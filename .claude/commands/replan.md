# /replan — Mid-Project Replanning Protocol

Triggered when: a new discovery, changed requirement, or rollback invalidates part
of the commit plan. Use this to formally revise `commit-protocol.md` with Team Lead approval.

Never use this to skip steps, combine commits, or reduce scope without explicit justification.

---

## Step 1 — State the trigger

Before drafting any changes, ask the Team Lead to confirm the trigger:

```
What triggered this replan?
[ ] Agent discovered mid-task that a planned commit is impossible or unnecessary
[ ] Rollback invalidated downstream commits
[ ] Requirement changed
[ ] New dependency discovered between commits
[ ] Other: ___
```

Do not proceed without a clear stated reason. The reason is logged permanently.

---

## Step 2 — Audit the current plan

Read `commit-protocol.md` in full. Read `project-state.json`.

Identify:
- All pending commits (not yet done)
- Which of those are affected by the trigger
- Any commits that now depend on something that no longer exists
- Any new commits that need to be added

---

## Step 3 — Draft the proposed change

Present the Team Lead with a structured diff of the plan:

```
## Proposed Replan — [date]

Trigger: [one sentence reason]

REMOVING:
  ✗ Commit [N] `[name]` — [why it's no longer needed]

ADDING:
  + Commit [N] `[new name]` — [what it does and why]
  Assigned to: [agent]
  Depends on: Commit [M]

REORDERING:
  Commit [X] `[name]` moves from position [old] → [new]
  Reason: [one sentence]

UNCHANGED: all other pending commits

Impact on agents:
  [Agent]: [one sentence on how their upcoming work changes]
```

Surface this to the Team Lead. Do not touch any file until approved.

---

## Step 4 — Team Lead approves

Wait for explicit confirmation: "Approved — apply the replan."

If the Team Lead requests modifications, revise the draft and re-surface.
Do not apply a partial or ambiguous approval.

---

## Step 5 — Apply the changes

**`commit-protocol.md`:**
- Remove commits: mark as `🗑 removed · [date] · [reason]`
- Add commits: insert in the correct position with full commit spec
- Reorder commits: update the table and renumber if needed

**`project-state.json`:**
- Update `commits_pending` list to reflect new sequence
- Add entry to `replan_history`

**Affected agent worklogs:**
Append a replan notice to each affected agent:

```markdown
## 📋 Replan Notice — [date]

The commit plan has been updated. Here is what changed for you:

What was removed: [commit name and why]
What was added: [commit name and what it requires]
What changed in your sequence: [one sentence]
Your next commit is now: Commit [N] `[name]`
```

---

## Step 6 — Brief the Team Lead

```
✅ Replan applied.

Changed: [summary of additions, removals, reorders]
Files updated: commit-protocol.md, project-state.json
Agents notified: [list]

Updated commit sequence (pending):
[N]  [name]  [agent]
[N+1] [name] [agent]
...

Ready to proceed with Commit [N] `[name]`. Shall I continue?
```

---

## Replan Non-Negotiables

- Never apply a replan without explicit Team Lead approval.
- Never remove a commit to reduce scope without a stated reason that's logged.
- Never add a commit that crosses an agent's domain boundary without confirming the agent.
- Every replan is recorded in `replan_history` — there is no informal restructuring.
- If the replan affects 5 or more commits, flag it as a major replan and ask the
  Team Lead whether a full re-archaeology pass is warranted before continuing.
