Generate and inspect a Phase A shadow context package without changing agent behavior.

Usage: `/context-preview [commit] [agent]`

Run:

```powershell
python hooks/build_codebase_graph.py
python hooks/build_agent_context.py --commit <commit> --agent <agent> --shadow
```

Then inspect `.context/runs/C<commit>-<agent>-shadow.json`.

Report:

- Selected files grouped by category
- Why each file was selected
- Missing or unresolved files
- Expansion triggers
- Budget usage
- Graph source and nearby hubs

This command is preview-only. Do not inject the generated package into an agent prompt.
