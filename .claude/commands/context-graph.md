# Build Context Graph

Build the cached Phase A structural graph without changing live agent prompts:

```powershell
python hooks\build_codebase_graph.py
```

Then preview a context package:

```powershell
python hooks\build_agent_context.py --commit $ARGUMENTS --agent rex --shadow
```

Inspect `.context/index/codebase-graph.json` for categories, imports, reverse
imports, and hub scores. Inspect `.context/runs/` for the bounded package that
an agent would receive.
