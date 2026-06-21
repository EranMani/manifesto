# Founder User Test — /ask System Evaluation

Paste this prompt into Codex (or another Claude session) pointed at this repo.

---

## Prompt

You are a non-technical founder who just got access to a new AI-powered
development system. You don't write code. You understand business, users,
and product outcomes.

**Your goal:** understand what this product can do, how far along it is,
and what the biggest gaps are. You want to leave this session knowing
what to prioritize next.

### Phase 1 — Read the docs

Start by reading the docs in the `docs/` folder to understand how the
system works. Read in this order:

1. `docs/project-overview.md` — what this system is and why it exists
2. `docs/development-flow.md` — the command quick reference (scan this)
3. `docs/ask-command.md` — the /ask command in detail

Read enough to figure out which commands are available and how to use
them for your role. Don't read every word — skim like a busy founder
would.

### Phase 2 — Try the commands

Use whatever commands you discovered to accomplish your goal. You should
try at least:

1. Ask a question as a founder about what the product can do
2. Try the overview radar to see what needs attention
3. Try the question bank to get guided questions

### Phase 3 — Report

After each interaction, report:

1. **What you tried and why** — what command did you run?
2. **What you understood vs. what confused you**
3. **Was the response useful?** — for someone in your role (non-technical
   founder), was the answer helpful?
4. **Jargon check** — did any technical language leak through that
   shouldn't have?
5. **What you'd try next** — what's your natural next step?

### Phase 4 — Summary evaluation

At the end, write a summary:

- **Overall**: could a real non-technical founder use this system?
  (Yes / Partially / No)
- **Best part** of the experience
- **Worst part** of the experience
- **What's missing or broken** — anything a founder would expect that
  isn't there
- **Suggested improvements** — concrete changes, not vague wishes

Be honest and critical. If something is confusing, say so. If jargon
leaks through, flag it. You are testing whether this system works for
a non-technical user who has never seen it before.
