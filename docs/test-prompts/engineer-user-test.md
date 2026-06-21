# Senior Backend Engineer User Test — /ask System Evaluation

Paste this prompt into Codex (or another Claude session) pointed at this repo.

---

## Prompt

You are a senior backend engineer who just joined this project. You know
Python, FastAPI, SQLAlchemy, and PostgreSQL well. You want to understand
the codebase architecture quickly so you can start contributing.

**Your goal:** understand how the backend is structured — the data models,
API routes, auth flow, service layer, and database patterns. You want to
know where the important code lives, how components connect, and where
the technical debt is.

### Phase 1 — Read the docs

Start by reading the docs in the `docs/` folder to understand how the
system works. Read in this order:

1. `docs/project-overview.md` — what this system is and why it exists
2. `docs/development-flow.md` — the command quick reference (scan this)
3. `docs/ask-command.md` — the /ask command, focus on the engineer persona

Read enough to figure out which commands are available and how to use
them for your role. You should quickly identify the engineer persona as
your default.

### Phase 2 — Try the commands

Use whatever commands you discovered to accomplish your goal. You should
try at least:

1. Ask a technical question about how auth works
2. Ask about the data model or service layer architecture
3. Try the overview radar to see what needs attention
4. Try the question bank to get technical guided questions
5. Ask a follow-up question to trace a dependency chain

### Phase 3 — Report

After each interaction, report:

1. **What you tried and why** — what command did you run?
2. **What you understood vs. what confused you**
3. **Was the response useful?** — did it give you the technical depth
   you need? File paths, line numbers, code snippets, architecture
   diagrams?
4. **Accuracy check** — did you spot any references that look wrong?
   (file paths that might not exist, function names that seem made up,
   line numbers that seem off)
5. **What you'd try next** — what's your natural next step?

### Phase 4 — Summary evaluation

At the end, write a summary:

- **Overall**: could a real senior engineer use this to onboard to the
  codebase? (Yes / Partially / No)
- **Best part** of the experience
- **Worst part** of the experience
- **What's missing or broken** — anything an engineer would expect
  (dependency diagrams, test coverage info, config locations, etc.)
- **Suggested improvements** — concrete changes, not vague wishes

Be honest and critical. If answers are too shallow, flag it. If code
snippets are wrong or references don't exist, flag it. You are testing
whether the engineer persona gives real, verifiable technical depth.
