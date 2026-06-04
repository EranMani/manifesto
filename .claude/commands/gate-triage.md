# /gate-triage — Quality Gate Triage

**When to invoke:** Step 8 of every commit loop — before spawning any reviewer agent.
Pass the staged diff. Receive a verdict: which reviewers fire, which skip, and why.

This skill replaces the inline matrix that previously lived in team-preferences.md.
Running it as an on-demand skill means the matrix costs zero tokens on commits where no gate runs.

---

## Input

Call with: `/gate-triage` followed by the `git diff --cached` output (or the diff summary for the current commit).

If no diff is provided, Claude reads `git diff HEAD~1` automatically.

---

## Triage Matrix

Evaluate each reviewer against the diff:

### Viktor — runs every 5th commit (C05, C10, C15, C20)
- Check: is this commit number divisible by 5?
- YES → **Viktor: RUN** (batch wave)
- NO → **Viktor: SKIP** (not this commit's wave)
- Model: haiku. Pass: `git diff` only, no full file contents. Token target: ≤20k.

### Sage — conditional
Run Sage if the diff touches ANY of:
- `dependencies.py` — get_current_user, require_role
- `core/security.py` — JWT, bcrypt
- `api/v1/auth.py` — login route
- `core/config.py` — env vars, secrets
- Any `.env` or `.env.example` file
- Any route that accepts user-supplied input in the request body
- External API calls (OpenAI, httpx to third parties)
- File upload or filesystem path operations

**Sage: RUN** if any of the above are present in the diff.
**Sage: SKIP** if the diff contains only: model files, migration files, stub routes (501 only), frontend components with no user-data rendering, doc-only changes, worklog changes.
- Model: haiku. Pass: targeted security-relevant files only, not full diff.

### Mira — conditional
Run Mira if the diff introduces or changes:
- A new page or UI component visible to the user
- An API response shape that changes what the user sees
- Any copy, label, or user-facing error message
- A new user interaction (form, button, redirect)

**Mira: RUN** if any of the above are present.
**Mira: SKIP** if the diff contains only: backend logic, migrations, config, stubs, hooks, docs, worklogs.
- Model: haiku. Pass: one-paragraph brief only — no diff, no files.

### Quinn — deferred (Phase 1)
Quinn is not active in Phase 1. Skip unconditionally until activated in AGENTS.md.

---

## Output Format

Emit exactly this block — nothing more:

```
## Gate Triage — Commit [N] `[name]`

Viktor:  [RUN (wave C[N]) | SKIP — next wave C[N]]
Sage:    [RUN — [reason, e.g. "auth route in diff"] | SKIP — [reason]]
Mira:    [RUN — [reason, e.g. "new Login page"] | SKIP — [reason]]
Quinn:   SKIP — deferred Phase 1

Reviewers to invoke: [list or "none"]
Invoke in parallel: [yes/no]
```

---

## Rules

- Never run a reviewer "just in case." No answer → skip.
- Never re-run a gate in the same commit loop after a fix. Blocking finding → new commit.
- If Viktor fires, always run first (or in parallel with Sage). Mira always last (advisory).
- Total reviewer token budget: ≤15k per reviewer. If you cannot fit within budget, compact first.
