Read `project-state.json`. Read `commit-protocol.md` for the next pending commit. Read the Current State Headers of all agents involved in or adjacent to this step.

Render this report:

---

## Handoff Check — Commit [N] `[commit-name]`

**Assignee:** [Agent]
**Depends on output from:** [list agents, or "None"]

---

## Required Handoffs

| From | To | Status | Summary |
|---|---|---|---|
| [Agent] | [Agent] | ✅ Present / ❌ Missing | [one sentence] |

---

## Open Handoffs (unactioned)

Any handoffs in `project-state.json` with status "unactioned" that affect this step:
`[From] → [To]: [description]`

---

## Verdict

Choose exactly one:

**✅ Clear to start** — all required handoffs are present. [Agent] can begin immediately.

**⚠️ Partially ready** — [what is present] / [what is missing]. The step can start but [Agent] should be aware of the missing context.

**🚫 Blocked** — required handoff from [Agent] is missing. Cannot start until resolved. Recommend surfacing to Team Lead.

---

## Recommended Action

One sentence: what the Team Lead should do right now.
