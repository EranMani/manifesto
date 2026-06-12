Prepare and invoke the approved delegated agent with surgical live context.

1. Read `project-state.json` and identify `next_commit` plus `next_commit_assignee`.
2. Confirm Eran has explicitly approved the Commit Preview. If not, stop and ask.
3. Confirm the approval card named a delegated executor and included a concrete
   delegation justification. Domain ownership alone is not justification. If execution
   was Claude-direct, stop; this command must not invoke an agent.
4. Run:

```powershell
python hooks/prepare_agent_delegation.py --commit <next_commit> --agent <assignee>
```

5. Read only `.context/delegations/C<NN>-<agent>.md`.
6. Invoke the named Agent with that brief verbatim. Do not duplicate file contents in
   the invocation prompt.
7. The agent reads listed files first. Additional search requires the expansion statement
   defined in the brief.
8. After the agent returns, verify changed paths against the brief's boundaries and the
   commit specification.

Never invoke the agent when the live package reports an unresolved authoritative contract
that blocks implementation. Surface that trigger to Eran first.
