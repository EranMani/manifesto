Prepare and invoke the owning agent with surgical live context.

1. Read `project-state.json` and identify `next_commit` plus `next_commit_assignee`.
2. Confirm Eran has explicitly approved the Commit Preview. If not, stop and ask.
3. Run:

```powershell
python hooks/prepare_agent_delegation.py --commit <next_commit> --agent <assignee>
```

4. Read only `.context/delegations/C<NN>-<agent>.md`.
5. Invoke the owning Agent with that brief verbatim. Do not duplicate file contents in
   the invocation prompt.
6. The agent reads listed files first. Additional search requires the expansion statement
   defined in the brief.
7. After the agent returns, verify changed paths against the brief's boundaries and the
   commit specification.

Never invoke the agent when the live package reports an unresolved authoritative contract
that blocks implementation. Surface that trigger to Eran first.
