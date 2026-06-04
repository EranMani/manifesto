Read `project-state.json` first (single source of truth). Then read `commit-protocol.md` for the full index. Then read the Current State Header (top ≤50 lines) of each active agent's worklog.

Render the report in this exact structure. Keep it under 50 lines total.

---

## Project Status — [project name] · [today's date]

### Commit Progress

| # | Name | Assignee | Status |
|---|---|---|---|
[Render every row. Status values:]
[✅ Done · [date]  — committed]
[🔄 WIP            — active session in worklog]
[⏳ Pending         — not started, no blockers]
[🚫 Blocked         — state the missing handoff or blocker]
[⏸ Parallel Wave   — part of a parallel group, awaiting wave trigger]

---

### Current Step

State the active or next step: commit number, name, assignee, and what it builds.
One sentence.

---

### Open Handoffs

For each handoff in `project-state.json` open_handoffs with status "unactioned":
`[From] → [To]: [one sentence summary]`

If none: "No open handoffs."

---

### Blockers

List anything that would prevent the next step from starting.
If none: "No blockers."

---

### Quality Gate Results (last commit)

`Tests: [PASS / FAIL / not run]`
`Viktor: [PASS / PASS WITH COMMENTS / BLOCKED / not run]`
`Sage: [not triggered / PASS / findings]`
`Quinn: [not triggered / ADEQUATE / NEEDS ADDITIONS]`

---

### Agent Activity

For each agent with a session in their worklog:
`[Agent name]: [last session task] — [✅ Done / 🔄 WIP]`

---

Keep the entire report under 50 lines. No commentary beyond what is asked for.
