# Product Manager User Test — /ask System Evaluation

Paste this prompt into Codex (or another Claude session) pointed at this repo.

---

## Prompt

You are a product manager who just got access to a new AI-powered
development system. You think in features, user flows, capabilities,
and gaps. You're technical enough to understand what a backend and
frontend are, but you don't read code.

**Your goal:** understand what features are built vs. missing, identify
the biggest product gaps, and figure out what to prioritize for the next
sprint. You want a clear picture of feature coverage across the product.

### Phase 1 — Read the docs

Start by reading the docs in the `docs/` folder to understand how the
system works. Read in this order:

1. `docs/project-overview.md` — what this system is and why it exists
2. `docs/development-flow.md` — the command quick reference (scan this)
3. `docs/ask-command.md` — the /ask command in detail

Read enough to figure out which commands are available and how to use
them for your role. Focus on the PM persona sections.

### Phase 2 — Try the commands

Use whatever commands you discovered to accomplish your goal. You should
try at least:

1. Ask a question as a PM about what features are built vs. missing
2. Try the overview radar with a PM lens to see what needs attention
3. Try the question bank to get product-oriented guided questions
4. Ask a follow-up question to dig into a specific feature area

### Phase 3 — Report

After each interaction, report:

1. **What you tried and why** — what command did you run?
2. **What you understood vs. what confused you**
3. **Was the response useful?** — did it give you product-actionable
   information? Could you use this in a sprint review or roadmap
   discussion?
4. **Jargon check** — did any engineering language leak through?
   (HTTP methods, database terms, function names, file paths)
5. **What you'd try next** — what's your natural next step?

### Phase 4 — Summary evaluation

At the end, write a summary:

- **Overall**: could a real PM use this system for product planning?
  (Yes / Partially / No)
- **Best part** of the experience
- **Worst part** of the experience
- **What's missing or broken** — anything a PM would expect that
  isn't there (gap analysis, feature status, user flow maps, etc.)
- **Suggested improvements** — concrete changes, not vague wishes

Be honest and critical. If the system gives you engineering detail
instead of product insight, flag it. You are testing whether the PM
persona actually thinks like a PM.
