Read `project-state.json` to find the current_commit. Then read `commit-protocol.md` for the full spec of that step. Then read the Current State Header of the owning agent's worklog. Then read the Current State Headers of any agents whose output this step depends on.

Execute in this order:

1. **Identify the step** — state the commit number, name, and assignee clearly.

2. **Check prerequisites** — verify all required handoffs are in place.
   - Check `project-state.json` open_handoffs for any addressed to the owning agent.
   - If any required handoff is unactioned: stop and tell the Team Lead what is blocking.

3. **Check quality gate results** — if the previous commit has unresolved Viktor concerns
   or Sage findings, surface them before proceeding.

4. **Brief the Team Lead** — in 3–5 bullet points:
   - What this step builds
   - Why it comes at this point in the sequence
   - What it unlocks for the steps that follow
   - Any token budget considerations for this invocation

5. **State the context package** — briefly describe what will be loaded for the agent:
   - Identity file: [agent].md
   - Handoffs: [list relevant handoffs or "none"]
   - Depth needed: Tier 1 only / Tier 2 (reason)

6. **Ask for approval** — end with exactly:

> Ready to begin **[commit name]** (Commit [N], assigned to [Agent]).
> Shall I proceed?

Do not start any work until the Team Lead confirms.
