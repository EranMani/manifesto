Read `project-state.json` to identify the next pending commit and owner. Check its
dependencies, open handoffs, and unresolved quality-gate findings. Then run:

`python hooks/prepare_agent_delegation.py --commit <N> --agent <agent-id>`

The generated preflight result and delegation package are internal preparation. When
preflight is ready, do not narrate prerequisite checks, sequence rationale, unlocks,
token commentary, selected-context counts, contracts, hubs, forbidden paths, graph
refreshes, or other package diagnostics.

For C29B and every later commit, the compact approval card must be the entire
response. Output no preamble, transition sentence, explanation, or conclusion before
or after it. The first output line must be `C[N] PREFLIGHT: ...` and the final output
line must be `Proceed? [yes/no]`.

Use exactly this card:

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

Resolve the owner name and domain from `hooks/agent-config.json`. Populate `Files`
exclusively from the commit specification's `Files To Modify Or Add` table. Do not list
automatically updated worklogs, telemetry, dashboards, domain maps, tool-cap state, or
other generated/runtime artifacts unless they are explicitly present in that table.
List every warning in plain language. Do not replace the card with a prose preview or
append a second approval question such as "Shall I proceed?"

Show additional diagnostics only when:

- preflight is blocked;
- a warning requires Eran's decision;
- approved scope changed;
- a split or repair invocation is proposed; or
- Eran explicitly asks for details.

Do not start work until Eran explicitly approves. After approval, invoke the owning
agent with the generated delegation brief verbatim. Do not duplicate full file contents
in the invocation prompt.
