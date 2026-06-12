Read `project-state.json` to identify the next pending commit and owner. Check its
dependencies, open handoffs, and unresolved quality-gate findings. Then run:

`python hooks/prepare_agent_delegation.py --commit <N> --agent <agent-id>`

The generated preflight result and delegation package are internal preparation. When
preflight is ready, do not narrate prerequisite checks, sequence rationale, unlocks,
token commentary, selected-context counts, contracts, hubs, forbidden paths, graph
refreshes, or other package diagnostics.

For C29B and every later commit, output only this compact approval card:

```text
C[N] PREFLIGHT: [READY|BLOCKED] ([score]/100)

Owner: [Name] ([Domain])
Goal: [one plain-language sentence]

Files:
- [Add|Edit|Delete]: path/to/file

Warnings:
- [Exact warning text, or "None."]
- Decision required: [Yes|No]

Proceed? [yes/no]
```

Resolve the owner name and domain from `hooks/agent-config.json`. List every planned
file and every warning in plain language. Do not replace the card with a prose preview
or append a second approval question such as "Shall I proceed?"

Show additional diagnostics only when:

- preflight is blocked;
- a warning requires Eran's decision;
- approved scope changed;
- a split or repair invocation is proposed; or
- Eran explicitly asks for details.

Do not start work until Eran explicitly approves. After approval, invoke the owning
agent with the generated delegation brief verbatim. Do not duplicate full file contents
in the invocation prompt.
