# /project-complete — Project Completion Protocol

Triggered when: all commits in `commit-protocol.md` are marked `✅ done`
and the Team Lead confirms the project is complete.

This command produces the final deliverables, captures institutional knowledge,
and closes the project in a state that future maintainers and future projects can build on.

---

## Step 1 — Confirm completion

Read `commit-protocol.md`. Verify every commit row shows `✅ done`.
Read `project-state.json`. Verify `commits_pending` is empty.

If any commit is still pending → do not run this command. Surface the gap to the Team Lead.

Ask the Team Lead: "All [N] commits are done. Shall I run the project completion protocol?"

---

## Step 2 — Run the retrospective synthesis

Read, in full:
- All agent worklogs (Current State Header + all sessions)
- `DECISIONS.md`
- `ARCHITECTURE.md`
- `GLOSSARY.md`
- `project-state.json` (quality_gate_results, rollback_history, replan_history)

Synthesize into `PROJECT_HANDOFF.md` (see template below).

---

## Step 3 — Produce PROJECT_HANDOFF.md

Create this file in the project root.

```markdown
# PROJECT_HANDOFF.md — [Project Name]

*Completed: [date]*
*Team Lead: [name]*
*Total commits: [N] over [X] days*

---

## What Was Built

[2–3 paragraph summary of the system. What it does, what problem it solves,
what the key architectural choices were. Written for someone reading this cold.]

---

## Architecture at Completion

[Copy the final state of ARCHITECTURE.md here, condensed to the essential diagram
and component list. Do not repeat the full doc — link to it.]

See full detail: `ARCHITECTURE.md`

---

## Key Decisions (Permanent Record)

[Extract the 5–10 most important entries from DECISIONS.md.
The ones that explain WHY the system works the way it does.
A future engineer who changes one of these without knowing the reason
will break something important.]

| Decision | Reason | Commit |
|---|---|---|
| [what was decided] | [why — one sentence] | [N] |

See full log: `DECISIONS.md`

---

## What Each Agent Built

### [Backend Agent Name]
[2–3 sentences. What they owned, key implementation choices, one thing that was harder than expected.]

### [DevOps Agent Name]
[2–3 sentences.]

### [AI Engineer Name] *(if active)*
[2–3 sentences.]

### [Frontend Agent Name] *(if active)*
[2–3 sentences.]

---

## Quality Gate Summary

| Metric | Value |
|---|---|
| Total commits | [N] |
| Viktor hard blocks raised | [N] |
| Sage CRITICAL/HIGH findings | [N] |
| Quinn INSUFFICIENT verdicts | [N] |
| Rollbacks | [N] |
| Replans | [N] |

**Recurring patterns Viktor flagged:** [list — these are the team's blind spots]
**Recurring patterns Sage flagged:** [list — these are the project's attack surface patterns]

---

## What Would We Do Differently

[Honest retrospective. 3–5 specific things. Not generic lessons — things that were
actually true in this project.]

1. [specific thing]
2. [specific thing]
3. [specific thing]

---

## Open Items at Handoff

[Anything that was scoped out, deferred, or left as known technical debt.]

| Item | Why deferred | Owner at handoff |
|---|---|---|
| [item] | [reason] | [team / person] |

---

## How to Run This System

[Minimal runbook. The 5 commands someone needs to know to operate this in production.]

```bash
# Start
[command]

# Run tests
[command]

# Deploy
[command]

# Check health
[command]

# Roll back a deployment
[command]
```

See full setup: `README.md`

---

## For the Next Team

[One paragraph addressed directly to whoever maintains or extends this.
What they absolutely must know before touching anything. What will break if they
don't understand X. Where the bodies are buried.]
```

---

## Step 4 — Write Agent Lessons

This is the step that makes the system compound over time. Do not skip it.
Do not write generic lessons. Generic lessons are loaded every session and activate nothing.

For each active agent, append structured lesson entries to the `## Lessons` section
of their identity file at `.claude/agents/[agent].md`.

---

### How to derive lessons — the process

For each agent, read in full:
- Their complete worklog (all sessions)
- Every quality gate finding directed at them
- Every handoff they sent and received
- The rollback_history and replan_history entries that involved them

Then ask three questions per agent:

1. **What situation kept recurring?**
   Recurring situations = the trigger for a lesson.
   If Viktor flagged the same pattern twice, that's a lesson.
   If a handoff broke down twice in the same way, that's a lesson.
   If an agent scope-overflowed the same type of work twice, that's a lesson.

2. **What was the consequence when it went wrong?**
   Lessons without consequences are advice. Consequences make lessons memorable.

3. **What's the precise pattern to apply next time?**
   Precise = file type, function type, stack type, situation type.
   Not "be more careful." "On any function that writes to >1 table, check transaction
   atomicity before reviewing the business logic."

---

### Lesson format — written into the agent's `## Lessons` section

Replace the `*No lessons yet*` placeholder with entries in this format:

```markdown
**[Project Name] · [Date]**
Trigger: [the specific situation that activates this lesson]
Pattern: [what to do or what to avoid — one sentence, concrete]
Why it matters: [the consequence — what broke or was avoided]
```

---

### What good lessons look like — per agent type

**Viktor:**
```
**Fintech API · 2026-03**
Trigger: Any service function that writes to more than one table in sequence
Pattern: Check transaction atomicity before reviewing business logic — multi-step
  writes must succeed together or fail together; look for explicit transaction blocks
Why it matters: Flagged this in commits 04, 07, and 11 — partial writes left
  orders in inconsistent state; earlier detection saves a full re-review cycle
```

**Sage:**
```
**Healthcare SaaS · 2026-06**
Trigger: Any route that returns user records, even internal-only routes
Pattern: Check for field-level filtering on every user data response — not just
  auth checks; unfiltered records expose PII even to authenticated users
Why it matters: A MEDIUM finding became HIGH when the client confirmed the route
  was accessible to support staff; caught late, cost a replan
```

**Quinn:**
```
**E-commerce Platform · 2026-05**
Trigger: Any service function that processes a list input (orders, items, cart)
Pattern: Always check the empty list case explicitly — business logic often
  silently returns success on empty input when it should return a validation error
Why it matters: Empty cart checkout passed all happy-path tests but created
  zero-value orders in the database — caught in staging, not production
```

**Backend Engineer:**
```
**SaaS Analytics · 2026-04**
Trigger: Any endpoint that aggregates data across multiple records
Pattern: Add explicit LIMIT clauses and pagination from the start — never assume
  the dataset is small enough to return in a single query
Why it matters: Worked fine in dev with 50 records; 30-second timeouts in
  production with 50K records; required an emergency hotfix commit
```

**DevOps Engineer:**
```
**Microservices Rebuild · 2026-07**
Trigger: Any new environment variable added to application code
Pattern: Add the variable to .env.example and docker-compose.yml in the SAME
  commit — never in a separate cleanup commit
Why it matters: 3 env vars missing from docker-compose for 4 days; local dev
  was broken with no clear error message
```

**Product Manager:**
```
**B2B Dashboard · 2026-08**
Trigger: Any commit that changes an existing API response shape
Pattern: Flag the frontend impact before approving — even small field renames
  break UI components in ways not obvious from the backend diff
Why it matters: A renamed field in commit 12 cascaded to 6 frontend components
  and required an unplanned replan
```

**Claude (Orchestrator):**
```
**Healthcare SaaS · 2026-06**
Trigger: Any session where two agents have both written handoff notes to each other
Pattern: Resolve circular handoffs immediately — do not queue them; they indicate
  a domain boundary misunderstanding that will compound
Why it matters: Circular handoffs in commits 09–11 required a mini-replan that
  cost 2 sessions of sequencing overhead
```

---

### Lesson quality checklist — verify before saving

- [ ] Every lesson has a Trigger, Pattern, and Why it matters
- [ ] No lesson uses "careful," "remember," or "make sure" without a specific action
- [ ] Every Pattern is precise enough that an agent knows exactly when to apply it
- [ ] No two lessons say the same thing in different words
- [ ] Every lesson came from a real event in the worklog — not from a template

If any lesson fails these checks, rewrite it before saving.

---

### Lesson volume limit — archive at 20 entries

The `## Lessons` section holds a maximum of 20 entries.

When 20 entries are reached:
1. Move the oldest 10 to `.claude/agents/[agent]-lessons-archive.md`
2. Keep the 10 most recent in the active file
3. Add a reference: `*Older lessons: [agent]-lessons-archive.md*`

The archive is never deleted. It is never loaded as Tier 0 context.
It exists for historical reference only.

---

## Step 5 — Update project-state.json

```json
{
  "status": "complete",
  "completed_date": "[ISO date]",
  "handoff_doc": "PROJECT_HANDOFF.md"
}
```

---

## Step 6 — Final message to Team Lead

```
✅ Project complete.

[Project name] — [N] commits over [X] days.

Deliverables:
  PROJECT_HANDOFF.md — full synthesis, decisions, runbook, retrospective
  Agent memory updated — [list of agents whose identity files were updated]

Quality summary:
  [N] Viktor hard blocks raised and resolved
  [N] Sage findings addressed
  [N] rollbacks, [N] replans

The system is ready for handoff or the next phase.
If a new phase begins — run /archaeology or /next-step to continue.
```
