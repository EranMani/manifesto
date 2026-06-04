# /pre-commit-doc-checklist — Pre-Commit Documentation Checklist

**When to invoke:** Step 9 of every commit loop — after the gate wave passes, before surfacing to Eran for approval.
Pass the commit number, commit name, and a brief summary of what was built.

This skill evaluates the 4-box checklist and proposes the exact edits needed — so Claude doesn't reason through it from scratch each time.

---

## Input

Call with: `/pre-commit-doc-checklist` followed by:
- Commit number and name (e.g. "C04 config-and-security")
- One paragraph: what was built in this commit
- The diff (or file list of what changed)

---

## The Four Checks

### Box 1 — DECISIONS.md
**Trigger:** Was a non-obvious design choice made? Did Andrej and Boris debate anything? Did an agent choose between two valid approaches?

Routine implementation of a spec = NO entry needed.
Any of these = YES, entry needed:
- A library, pattern, or approach was chosen over an alternative
- A constraint was discovered that isn't in the spec
- An agent deviated from the spec and logged why
- A cross-domain finding changed an earlier decision

**Output if YES:** Draft the DECISIONS.md entry title and one-sentence summary. Claude writes the full entry.
**Output if NO:** "DECISIONS.md — no new entry needed."

### Box 2 — ARCHITECTURE.md
**Trigger:** Was a new component, service, data flow, or integration introduced?

New file in `backend/app/` that other files will import = YES.
New React page or component that introduces a new UI pattern = YES.
Config tweak, stub route, seed script, migration only = NO.

**Output if YES:** State exactly which section of ARCHITECTURE.md needs updating and what to add (component name, what it does, what it connects to).
**Output if NO:** "ARCHITECTURE.md — no update needed."

### Box 3 — GLOSSARY.md
**Trigger:** Was a new term introduced that a new team member wouldn't know?

Domain-specific terms (e.g. "policy chunk", "logistics chat", "LLMService", "pgvector"), new acronyms, or project-specific concepts = YES.
Standard Python/React/SQL terms = NO.

**Output if YES:** Draft the term and one-sentence definition.
**Output if NO:** "GLOSSARY.md — no new terms."

### Box 4 — TOKEN_RECORDS.md
**Trigger:** Always. Every commit gets an entry.

**Output:** The exact table row to append, with placeholders for token counts Claude fills in from the Agent tool call `<usage>` block:

```
| C[N] | [name] | [agent] | [model] | [tokens] | [tool uses] | [±vs target] |
```

If multiple agents were invoked (e.g. implementor + reviewer), one row per agent.

---

## Output Format

Emit exactly this block:

```
## Pre-Commit Doc Checklist — Commit [N] `[name]`

DECISIONS.md:   [entry needed: "[title]" | no entry needed]
ARCHITECTURE.md:[update needed: "[section] — [what to add]" | no update needed]
GLOSSARY.md:    [new terms: "[term] — [definition]" | no new terms]
TOKEN_RECORDS.md: [row ready — fill token counts from <usage> block]

Actions for Claude:
1. [specific edit or "none"]
2. [specific edit or "none"]
3. [specific edit or "none"]
4. Append TOKEN_RECORDS.md row after token counts confirmed
```

---

## Rules

- Do not hallucinate decisions. If unsure whether a choice was non-obvious, ask: "Would a new engineer reading only the spec understand why this was done this way?" If no — log it.
- ARCHITECTURE.md and DECISIONS.md entries are written by Claude immediately — not deferred.
- TOKEN_RECORDS.md row is written last, after all agent `<usage>` blocks are confirmed.
