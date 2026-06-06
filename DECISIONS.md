# DECISIONS.md — Manifesto

> Maintained by Claude. Every non-obvious design choice made during this project
> is logged here with the reason it was made — including the debate that led to it.
> Last updated: 2026-06-04

---

## How to read this file

Each entry captures three things: what was decided, why alternatives were rejected,
and — where a real debate happened — the actual back-and-forth between Andrej and Boris.
The debates are the most valuable part. They show the thinking, not just the conclusion.

---

## D01 — Phase 1 Commit Index Structure

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Pre-development. Planning the Phase 1 commit sequence before any code is written.

### The debate

**Andrej's initial proposal** was a 21-commit index sequenced as: infrastructure → python skeleton → frontend scaffold → config → database → models → migration → auth → routes → stubs → seed → frontend pages → login → smoke test.

**Boris raised three objections:**

**Objection 1 — `main.py` coupling across commits.**
Every route commit (C09–C13) touches `main.py` to call `include_router`. This makes `main.py` a shared file that multiple commits modify, creating implicit coupling. Boris flagged this as a coordination smell.

Andrej's response: Rex owns `main.py` sequentially — there's no concurrent modification risk since Rex owns all backend commits. The touches are clean because they're additive (append-only). Convention: `main.py` gets a `# routers registered below` comment block in C02, and each route commit appends. Accepted as-is.

**Objection 2 — Seed script placed too late (C16).**
The original index put `seed.py` after all routes were built. But Rex needs a real credential to test auth manually during C08–C10. Without seed data, auth testing is blind.

Andrej conceded immediately. Seed moved to C08, immediately after the Alembic migration (C07). The dependency chain becomes `C07 → C08 → C09` (migration → seed → auth), which is strictly correct.

**Objection 3 — C21 smoke test wrong owner.**
Original draft assigned the integration smoke test to Rex. Boris argued: Rex built the application layer; Adam owns docker-compose and the assembled container stack. "Does the stack run" is an infrastructure concern, not a backend concern. The smoke test is Adam verifying the assembled system, not Rex verifying his own routes.

Andrej conceded. C21 → Adam.

**Boris's final push on parallelization:**
C03 (frontend scaffold) has zero dependency on C01 or C02 — it's pure frontend with no shared files. It should be explicitly marked `∥ C02` in the index, not just "noted as parallelizable."

Andrej agreed. Marked explicitly.

### Decision

21-commit index, phased as:
- Phase 1A: Infrastructure foundation (C01–C03, C03 ∥ C02)
- Phase 1B: Backend core — config, DB session, models, migration, seed (C04–C08)
- Phase 1C: Auth and user management (C09–C11)
- Phase 1D: Inventory routes (C12–C14)
- Phase 1E: Service stubs (C15–C16)
- Phase 1F: Frontend core — store, routing, placeholders, login (C17–C20)
- Phase 1G: Integration verification (C21, Adam)

### Consequences

- Each commit has one owner and one concern — clean revert boundary on every step
- Seed data exists before any auth route is built — Rex can test with real credentials from C09 onward
- Smoke test is owned by infrastructure, not the application layer — correct domain boundary
- Frontend scaffold can run in parallel with Python skeleton — time saved on early sessions

---

## D02 — Package Manager: uv over pip/requirements.txt

- **Date:** 2026-06-04
- **Decided by:** Eran
- **Context:** C02 (python-skeleton) originally specified `requirements.txt`. Eran directed switch to `uv`.

### Decision

Use `uv` as the Python package manager. `pyproject.toml` replaces `requirements.txt`.

### Rationale

`uv` is significantly faster than pip for installs (Rust-based resolver). It is the modern standard for Python project management. Lock file (`uv.lock`) provides reproducible installs without the overhead of manual `requirements.txt` maintenance.

### Consequences

- C02 produces `pyproject.toml` + `uv.lock` instead of `requirements.txt`
- Dockerfile uses `uv sync` instead of `pip install -r requirements.txt`
- All agents working in the backend must use `uv add <package>` not `pip install`

---

## D03 — Agent Roster: Lean Start, Add Later

- **Date:** 2026-06-04
- **Decided by:** Eran
- **Context:** rag-from-scratch used 11 agents at peak. Manifesto Phase 1 has no AI layer yet.

### Decision

Start with the minimum viable roster. Add agents when their domain becomes active.

**Active from Phase 1:**
- Rex (backend) — owns all Python application code
- Adam (devops) — owns all infrastructure
- Aria (frontend) — owns all React/TypeScript
- Viktor (reviewer) — quality gate, every 5 commits
- Sage (security) — conditional, auth/secrets/input routes only
- Mira (product) — conditional, user-facing behavior changes only

**Deferred:**
- Nova (AI engineer) — activates Phase 2 when LLMService is wired
- Quinn (QA) — activates Phase 2 when business logic warrants coverage review
- Ryan (tech writer) — activates Phase 4 hardening
- Lara (curriculum) — not applicable to this project

### Consequences

- Smaller context packages per invocation — fewer agent identity files loaded
- Quality gate wave is leaner — Viktor + Sage only (not 4 parallel reviewers)
- Agents are added by writing their identity file and registering in AGENTS.md — no ceremony

---

## D04 — Commit Preview Format: "Summary" replaces "What"

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** First Commit Preview rendered for C01. Eran asked: would a junior developer understand this?

### The debate

**Andrej's position:** The preview optimized entirely for the approval decision — technical gates, file paths — and gave nothing to the learning reader. A 1-2 sentence plain-English summary at the top costs ~30 tokens and pays back every time Eran reads a preview without needing to mentally reconstruct what the commit does from the file list.

**Boris's constraint:** The summary must not duplicate the "What" line. If we add a summary, "What" becomes redundant — paying tokens for the same information twice. Fix: replace "What" with the plain-English summary. One field, two jobs.

**Andrej conceded and extended:** Correct. "Why now" already handles sequencing. So the structure becomes Summary (human-readable, replaces What) + Why now (sequencing) + everything else unchanged. Zero tokens added, one field renamed.

**Two additional changes agreed:**
- Parallel callout moved above Changes — it's an approval-time decision, not a footnote
- Quality gate always stated explicitly — "None" implied the check was skipped; the rule statement shows the system is working as designed

### Decision

Replace "What" with "Summary" in the Commit Preview format. Summary is 1-2 sentences, plain English, junior-readable. Parallel callout moves above Changes. Quality gate line always states the rule, never "None".

### Consequences

- Any reader — including a junior developer — can understand a commit from the Summary line alone
- No token cost increase — same field count, one renamed
- Explicit quality gate line builds Eran's understanding of when and why gates trigger

---

## D05 — Token Optimization Strategy: What We Adopt and What We Reject

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Pre-development review of 4 published token optimization strategies before C01 begins.

### Strategy 1 — Codebase indexing (CodeGraph)

**Initial position (Andrej):** Domain boundaries make this redundant — Rex doesn't scan `frontend/`, so a graph adds no value.

**Boris's reversal:** Correct for cross-domain reads, but wrong for within-domain navigation. As `backend/app/` grows across 15+ commits, Rex will spend tool uses tracing import chains internally. A pre-built domain graph lets him query structure instead of reading 4 files to answer one structural question.

**Decision:** Build lightweight per-domain import graphs scoped to each agent's domain only. Rex gets a graph of `backend/`. Aria gets a graph of `frontend/src/`. Implemented as a post-commit hook script (`hooks/generate_domain_map.py`) that writes `backend/DOMAIN_MAP.md` and `frontend/DOMAIN_MAP.md`. No agent sees the full project graph — domain boundaries preserved.

**Deferred:** Not built before C01. Added to the pre-C01 build list for the next preparation session.

### Strategy 2 — Output compression (RTK)

**Decision:** Adopt the principle, skip the library. Two additions to execution constraints in `team-preferences.md`:
- Verbose command output rules: alembic and pytest return summary line + any ERROR/FAIL lines only
- Bash filter snippets for known-verbose commands

Rationale: Our agents don't consume raw logs by default. The problem only manifests on specific commands. A one-line convention in the invocation prompt costs zero tokens and solves the same problem.

### Strategy 3 — Forced output shortening (Caveman)

**Decision:** Reject. Worklogs and handoffs are the connective tissue of the system — truncating them degrades the context loop on subsequent invocations. The 25-tool cap and one-write-at-completion rule already enforce discipline without sacrificing meaning. The risk is asymmetric: save tokens on output, pay more on the next invocation when the agent re-derives lost context.

### Strategy 4 — Session management

**Decision:** Already implemented at a high level. Four specific improvements added from the debate:

1. **No speculative file reads mid-session.** No file reads that aren't directly required by the active commit spec. Every speculative read compounds across session history.
2. **Agent warm/cold context distinction.** Fresh agent (no worklog) → Tier 0 only. Continuing agent (3+ commits) → Tier 0 + Current State Header. No full worklog history passed by default.
3. **Token checkpoint before gate wave.** If session tokens > 40k before spawning Viktor/Sage/Mira → `/compact` first, then run the gate wave.
4. **Commit Preview as natural checkpoint.** If session tokens > 30k at Preview time and no agent has been invoked yet → `/compact` before proceeding.

---

## D06 — Gate-Triage: Skill vs. Inline Matrix

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Gate-triage matrix currently lives in `team-preferences.md` and `AGENTS.md` — always loaded, always consuming tokens.

### The debate

**Boris (initial):** The matrix is already in `team-preferences.md` — Claude reads it at boot. Making it a skill adds invocation overhead for a decision Claude should already be making. Encoding it twice adds maintenance burden.

**Andrej's reversal:** Boris was wrong on this one, and the logic is sound. The matrix in `team-preferences.md` is *always* loaded — it costs tokens whether it's needed or not. Moving it to a skill means it's loaded only when Claude explicitly invokes it. Smaller always-loaded files, on-demand logic. Net token reduction.

**Boris's risk flag:** If Claude forgets to invoke the skill, the gate decision gets made without the matrix. Mitigation: make invocation mandatory and mechanical — the commit loop protocol says "Step 8 always starts with `/gate-triage`." Not a judgment call — a protocol step.

### Decision

Build `gate-triage` as a skill. Remove the full matrix from `team-preferences.md` — keep only the pointer: "Step 8: invoke `/gate-triage` with the diff." Matrix logic lives in the skill only.

### Consequences

- Always-loaded files (`team-preferences.md`, `AGENTS.md`) shrink
- Gate logic is on-demand — zero cost on commits where no gate runs
- Risk: invocation must be mechanical (protocol step), not optional

---

## D07 — Skills Build List: What to Build Before C01

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** 21 skill ideas in skillsmith/skills_ideas reviewed against Manifesto's needs.

### Skills to build now (before C01)

| Skill | Rationale |
|---|---|
| `gate-triage` | Replaces inline matrix — on-demand, token-efficient |
| `pre-commit-doc-checklist` | Evaluates DECISIONS/ARCHITECTURE/GLOSSARY checklist against diff — saves Claude reasoning tokens every commit |
| `parallel-wave-detector` | Detects parallelizable commits — gets harder to reason manually as project grows |

### Infrastructure to build now

| Item | Rationale |
|---|---|
| `hooks/generate_domain_map.py` | Per-agent import graph, scoped to domain, updated post-commit |
| `TOKEN_RECORDS.md` | Token usage tracker — schema defined now, first entry after C01 |
| `team-preferences.md` updates | Verbose output rules, session checkpoint rules, gate-triage pointer |

### Skills deferred

Everything else from the 21-idea catalog — either already implemented as project files (`agentic-workflow-bootstrap`, `hook-bundle-installer`), applicable only Phase 2+ (`commit-spec-from-issue`, `repo-risk-surface-map`), or redundant with existing conventions (`tool-cap-enforcer`, `worklog-current-state`).

---

## D08 — TOKEN_RECORDS.md: Schema and Purpose

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Token measurement needed to track cost per commit and per agent, validate optimization strategies over time.

### Schema (per commit entry)

```
| Commit | Agent | Model | Tokens | Tool uses | vs. Target |
```

One row per agent invocation. Session total at the bottom. Delta vs. target shows whether optimization strategies are working.

### Rules

- Updated by Claude before every approval prompt — no agent needed
- Token counts come from the `<usage>` block returned by each Agent tool call
- First entry: C01 after Adam completes
- File must never be estimated — exact counts only. An estimated entry is worse than no entry.

### Why this matters

Without measurement, token reduction is guesswork. `TOKEN_RECORDS.md` is the instrument that tells us whether the per-domain graphs, skill extractions, and session checkpoints are actually reducing cost — or just adding complexity.

---

## D09 — Git Hook: sh Wrapper Instead of Direct Python Copy (Windows)

- **Date:** 2026-06-04
- **Decided by:** Adam (C01 execution)
- **Context:** `hooks/pre_commit_check.py` has a `#!/usr/bin/env python3` shebang. On Windows, Git for Windows runs hooks through its bundled `sh`. A bare `.py` file is not reliably executable there because `python3` is not always on PATH in Git's sh environment.

### Decision

Install `.git/hooks/pre-commit` as a POSIX sh wrapper that explicitly calls `python hooks/pre_commit_check.py` rather than copying the `.py` file directly.

### Rationale

The wrapper pattern is portable: Git's sh executes the wrapper; the wrapper calls Python with an explicit path. Direct copy would require `python3` to be on PATH within Git's sh environment — not guaranteed on Windows.

### Consequences

- Pre-commit hook works reliably on Windows Git for Windows
- The hook file at `.git/hooks/pre-commit` is a small sh wrapper, not the Python script itself
- If `hooks/pre_commit_check.py` is moved, the wrapper path must be updated

---

## D10 — Pre-Commit Hook: COMMIT_EDITMSG Pre-Write Workaround (Windows)

- **Date:** 2026-06-04
- **Decided by:** Claude (orchestrator, C01 commit)
- **Context:** On this Windows setup, `git commit -m "message"` does not update `.git/COMMIT_EDITMSG` before the pre-commit hook runs. The hook reads the stale previous commit's message, causing false format validation failures.

### Decision

Pre-write `.git/COMMIT_EDITMSG` with the intended commit message immediately before every `git commit -m` call. Git overwrites it with the same content anyway — the pre-write ensures the hook reads the correct message.

Also: the `Co-Authored-By` regex in `pre_commit_check.py` uses `\S+\s+<email>` — it expects a single-word name before the email. Multi-word names like "Claude Sonnet 4.6" are not matched. Convention: use single-word agent names in `Co-Authored-By` trailers (e.g., `Co-Authored-By: Adam <adam@manifesto.local>`).

### Consequences

- Every commit requires a two-step pattern: `printf ... > .git/COMMIT_EDITMSG`, then `git commit -m`
- Co-Authored-By must use single-word names matching agent-config.json keys
- This should be investigated in C21 (Adam's smoke test) to see if a hook fix is preferable

---

## D11 — postcss.config.js: Required but Absent from Spec

- **Date:** 2026-06-04
- **Decided by:** Aria (C03 execution)
- **Context:** `commit-03.md` spec did not list `postcss.config.js`. Aria encountered a build failure without it.

### Decision

Add `postcss.config.js` to `frontend/` alongside the spec files.

### Rationale

Tailwind CSS v3 requires PostCSS to process `@tailwind` directives at build time. Without `postcss.config.js`, Vite's CSS pipeline does not invoke Tailwind at all — the build succeeds but all Tailwind classes are stripped. This is a mechanical requirement of the declared stack (Tailwind v3 + Vite), not a design choice.

### Consequences

- `frontend/postcss.config.js` exists from C03 onward; no commit needed later
- All future commit specs involving Tailwind may assume PostCSS is configured
- Spec omission noted — future specs should include it when listing Tailwind as a dependency

---

## D12 — Pre-Commit Hook: GIT_MESSAGE Priority Order Fix

- **Date:** 2026-06-04
- **Decided by:** Aria (C03 execution), retroactively noted by Claude
- **Context:** Pre-commit hook's `get_commit_message()` originally checked `COMMIT_EDITMSG` before the `GIT_MESSAGE` env var. On Windows, `COMMIT_EDITMSG` contains the *previous* commit's message when the pre-commit hook fires (git hasn't written the new message yet). This caused format validation failures on every commit.

**Updates D10:** D10 described a workaround — pre-write `COMMIT_EDITMSG` before every `git commit -m` call. This fix eliminates the need for that workaround.

### Decision

In `get_commit_message()`, check `GIT_MESSAGE` env var **first**, fall back to `COMMIT_EDITMSG`, then return `""`.

### Rationale

`GIT_MESSAGE` is explicitly set by commit wrappers and CI before calling `git commit`. It is always the intended message. `COMMIT_EDITMSG` at pre-commit time contains the prior commit's message on Windows — an unreliable source. The priority inversion was the root cause of D10's pre-write workaround.

### Consequences

- `GIT_MESSAGE` must be set in the environment before `git commit -m` is called
- D10's pre-write-COMMIT_EDITMSG workaround is no longer needed but remains harmless if done
- Sage confirmed this change cannot be exploited: message still passes through the conventional-commit format validator regardless of source

---

## D13 — Commit Protocol: Claude Commits on Eran's Behalf After Approval

- **Date:** 2026-06-05
- **Decided by:** Eran
- **Context:** Every commit required Eran to manually run `ERAN_COMMIT=1 git commit -m "..."`. Agents were not appearing as GitHub contributors because no `Co-Authored-By` trailers were being added.

### Decision

After Eran approves a commit, Claude commits on his behalf using:
```
GIT_MESSAGE="<msg>" CLAUDE_COMMIT=1 git commit -m "<msg>"
```
with `Co-Authored-By` trailers for the agent who did the work.

`CLAUDE_COMMIT=1` is a new bypass added to `block_agent_commit.py` — distinct from `ERAN_COMMIT=1` so the two paths remain distinguishable in the hook.

### Commit message format

```
type(scope): imperative subject line (max 72 chars)

2-3 sentences, plain English: what changed and why it matters.
No internal jargon (no "D13", "C05 governance sync", etc.).

Co-Authored-By: AgentName <agent@email>
Co-Authored-By: Claude <claude@anthropic.com>
```

Types: `feat / fix / chore / refactor / test / docs`
Scopes: `backend / frontend / devops / config / governance`

### Co-Authored-By convention

- Names must be single-word (D10 constraint: pre-commit hook regex `\S+\s+<email>`)
- Emails from `hooks/agent-config.json`
- Agent work: `Co-Authored-By: Rex <rex.stockagent@gmail.com>` etc.
- Claude direct writes: `Co-Authored-By: Claude <claude@anthropic.com>`
- Always add Claude as co-author on all commits (orchestrator)
- `GIT_MESSAGE` env var must contain the full message including trailers (hook validates from it)

### Consequences

- Agents appear as GitHub contributors on every commit they own
- Eran no longer needs to run any git command after approval
- Implementor agents (Rex, Adam, Aria) still cannot commit — their constraint is unchanged

---

*This document records decisions as they are made. Update it before every Team Lead approval prompt when a non-obvious choice was made.*
it Preview Format: "Summary" replaces "What"

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** First Commit Preview rendered for C01. Eran asked: would a junior developer understand this?

### Decision

Replace "What" with "Summary" in the Commit Preview format. 1-2 sentences, plain English, junior-readable. Parallel callout moves above Changes. Quality gate line always states the rule explicitly, never "None".

### Consequences

- Any reader can understand a commit from the Summary line alone
- No token cost increase — same field count, one field renamed
- Explicit quality gate line builds Eran's understanding of when and why gates trigger

---

## D05 — Token Optimization Strategy: What We Adopt and What We Reject

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)

| Strategy | Verdict |
|---|---|
| CodeGraph indexing | Adopt as per-agent domain graphs (not full-project) |
| Log compression (RTK) | Adopt principle as execution constraint — no library |
| Caveman output truncation | Reject — degrades context loop |
| Session management | Already implemented + 4 new checkpoint rules added |

Per-domain graphs: Rex gets `backend/DOMAIN_MAP.md`, Aria gets `frontend/DOMAIN_MAP.md`. Generated by `hooks/generate_domain_map.py` post-commit. Scoped to agent domain only — domain boundaries preserved.

---

## D06 — Gate-Triage: Skill vs. Inline Matrix

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)

Gate triage matrix moved from `team-preferences.md` to `.claude/commands/gate-triage.md`. On-demand only — costs zero tokens on commits where no gate runs. Pointer in `team-preferences.md`: "Step 8: invoke `/gate-triage` with the diff." Invocation is a mandatory protocol step, not a judgment call.

---

## D07 — Skills Build List: What to Build Before C01

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)

Built: `gate-triage`, `pre-commit-doc-checklist`, `parallel-wave-detector` skills. `hooks/generate_domain_map.py`. `TOKEN_RECORDS.md`. Updated `team-preferences.md` with verbose output rules, session checkpoints, agent context tiers.

---

## D08 — TOKEN_RECORDS.md: Schema and Purpose

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)

Schema: `| Commit | Agent | Model | Tokens | Tool uses | vs. Target |` — one row per agent invocation, exact counts from `<usage>` block. Updated by Claude before every approval prompt. Estimated entries banned.

---

## D09 — Git Hook: sh Wrapper Instead of Direct Python Copy (Windows)

- **Date:** 2026-06-04
- **Decided by:** Claude (orchestrator, C01 commit)
- **Context:** On Windows, `.git/hooks/pre-commit` must be a shell script — a raw Python file with no shebang is not executable by git-bash.

### Decision

`.git/hooks/pre-commit` is a small sh wrapper: `#!/bin/sh\npython hooks/pre_commit_check.py "$@"`. Not a copy of the Python file.

---

## D10 — Pre-Commit Hook: COMMIT_EDITMSG Pre-Write Workaround (Windows)

- **Date:** 2026-06-04
- **Decided by:** Claude (orchestrator, C01 commit)
- **Context:** On this Windows setup, `git commit -m "message"` does not update `.git/COMMIT_EDITMSG` before the pre-commit hook runs.

### Decision

Every commit uses a two-step pattern: `printf ... > .git/COMMIT_EDITMSG`, then `git commit -m`. Co-Authored-By must use single-word agent names matching agent-config.json keys.

---

## D11 — Agent Commit Blocker: ERAN_COMMIT=1 Bypass Pattern

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (analysis of /insight report), Eran (approval)
- **Context:** /insight report showed 9 dissatisfied moments across 5 sessions. Primary cause: Aria committed without approval (gate-triage bypass), governance docs updated partially, encoding fix cascaded into blocking Eran's next commit.

### The problem

Protocol rules live in files. Files don't enforce themselves. Between session resets, Claude loses working context of stored preferences — the same violations recur because the enforcement layer was trust-based, not mechanical.

### Decisions

**1. `block_agent_commit.py` — PreToolUse hook on Bash**
Intercepts any bash command containing `git commit`, `git push`, `git merge`, `git rebase`.
Blocks with exit 2 and a clear message. Eran bypasses with `ERAN_COMMIT=1 git commit -m "..."`.
Agents never set this env var — they are always blocked mechanically.

**2. CLAUDE.md Critical Rules callout at the very top**
Four rules added as the first block in CLAUDE.md, before the boot sequence:
- Always address Eran by name
- Never commit without Eran's explicit approval
- When updating any governance file, update all related files in the same pass
- Before staging, verify domain ownership

**3. Governance sync check added to pre-commit-doc-checklist skill**
When any governance file changes, the skill greps for related files and flags missed updates.
Related file map defined: editing commit-protocol.md → also check project-state.json + team-preferences.md, etc.

**4. Root-cause discipline rule**
If a fix fails once, stop patching symptoms. State the root-cause hypothesis explicitly before trying another approach. (From the Chroma health-check session in rag-from-scratch — 3+ failed attempts before the real cause was found.)

### Consequences

- Aria-style unauthorized commits are mechanically impossible — hook blocks before git runs
- Eran can commit freely: `ERAN_COMMIT=1 git commit -m "..."`
- Partial governance updates are caught by the skill's sync check before approval is surfaced
- The same enforcement now exists in CLAUDE.md (read every session) + hooks (run every commit)

---

*This document records decisions as they are made. Update it before every Team Lead approval prompt when a non-obvious choice was made.*

**Boris's risk flag:** If Claude forgets to invoke the skill, the gate decision gets made without the matrix. Mitigation: make invocation mandatory and mechanical — the commit loop protocol says "Step 8 always starts with `/gate-triage`." Not a judgment call — a protocol step.

### Decision

Build `gate-triage` as a skill. Remove the full matrix from `team-preferences.md` — keep only the pointer: "Step 8: invoke `/gate-triage` with the diff." Matrix logic lives in the skill only.

### Consequences

- Always-loaded files shrink
- Gate logic is on-demand — zero cost on commits where no gate runs
- Risk: invocation must be mechanical (protocol step), not optional

---

## D07 — Skills Build List: What to Build Before C01

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)

Built: `gate-triage`, `pre-commit-doc-checklist`, `parallel-wave-detector` skills. `hooks/generate_domain_map.py`. `TOKEN_RECORDS.md`. Updated `team-preferences.md` with verbose output rules, session checkpoints, agent context tiers.

---

## D08 — TOKEN_RECORDS.md: Schema and Purpose

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)

Schema: `| Commit | Agent | Model | Tokens | Tool uses | vs. Target |` — one row per agent invocation, exact counts from `<usage>` block. Updated by Claude before every approval prompt. Estimated entries banned.

---

## D09 — Git Hook: sh Wrapper Instead of Direct Python Copy (Windows)

- **Date:** 2026-06-04
- **Decided by:** Claude (orchestrator, C01 commit)

`.git/hooks/pre-commit` is a small sh wrapper calling `python hooks/pre_commit_check.py`. On Windows, a raw Python file with no shebang is not executable by git-bash.

---

## D10 — Pre-Commit Hook: COMMIT_EDITMSG Pre-Write Workaround (Windows)

- **Date:** 2026-06-04
- **Decided by:** Claude (orchestrator, C01 commit)

On this Windows setup, `git commit -m "message"` does not update `.git/COMMIT_EDITMSG` before the pre-commit hook runs. Every commit uses a two-step pattern: `printf ... > .git/COMMIT_EDITMSG`, then `git commit -m`. Co-Authored-By must use single-word agent names matching agent-config.json keys.

---

## D11 — Agent Commit Blocker: ERAN_COMMIT=1 Bypass Pattern

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (analysis of /insight report), Eran (approval)
- **Context:** /insight report (5 sessions, 47 messages): 9 dissatisfied moments, 1 happy. Primary violations: Aria committed without approval, governance docs updated partially, encoding fix missed a file and cascaded into blocking Eran's next commit.

### Root cause

Protocol rules live in files. Files don't enforce themselves. Between session resets, Claude loses working context of stored preferences — the same violations recur because the enforcement layer was trust-based, not mechanical.

### Decisions made

**1. `hooks/block_agent_commit.py` — PreToolUse hook on Bash**
Intercepts bash commands containing `git commit`, `git push`, `git merge`, `git rebase`. Blocks with exit 2. Eran bypasses with `ERAN_COMMIT=1 git commit -m "..."`. Agents never set this env var — blocked mechanically.

**2. CLAUDE.md Critical Rules callout at the very top**
Four rules added before the boot sequence — first thing read every session:
- Always address Eran by name
- Never commit without Eran's explicit approval
- When updating any governance file, update all related files in the same pass (grep to verify)
- Before staging, verify domain ownership

**3. Governance sync check added to pre-commit-doc-checklist skill**
Related file map defined — editing one governance file triggers a check of all related files. Must reach "Governance sync: CLEAN" before approval is surfaced.

**4. Root-cause discipline**
If a fix fails once, stop patching symptoms. State the root-cause hypothesis explicitly before trying another approach.

### Consequences

- Aria-style unauthorized commits are mechanically impossible
- Eran commits freely: `ERAN_COMMIT=1 git commit -m "..."`
- Partial governance updates caught by skill sync check before approval surfaces
- Same enforcement exists in CLAUDE.md (read every session) + hook (runs every commit)

---

## D21 — Admin Route PUT: user_id Typed as str, Not UUID

- **Date:** 2026-06-05
- **Decided by:** Rex (C11 execution)
- **Context:** `PUT /api/v1/admin/users/{user_id}` path parameter. The `User.id` column is declared `UUID(as_uuid=False)` — SQLAlchemy stores it as a plain Python string, not a `uuid.UUID` object. FastAPI path-param coercion to `uuid.UUID` would cause a silent type mismatch in the `WHERE User.id == user_id` query.

### Decision

Type `user_id` as `str` in the route signature, not `UUID`.

### Rationale

Matching the path param type to the storage representation avoids a silent comparison failure. Casting to `UUID` and back adds noise with no practical benefit.

### Consequences

- All routes querying by ID on `UUID(as_uuid=False)` columns must use `str` path params
- C12–C14 routes should follow the same convention for their respective ID columns
- If `User.id` is ever migrated to `UUID(as_uuid=True)`, all affected path params need revisiting

---

*This document records decisions as they are made. Update it before every Team Lead approval prompt when a non-obvious choice was made.*

---

## D13 — Local Validation: npm install Must Run Before npm run build

- **Date:** 2026-06-04
- **Decided by:** Observed during C03 local validation
- **Context:** `npm run build` failed with `'tsc' is not recognized` on Eran's machine after C03 was marked done.

### Root cause

Session notes recorded "npm install and npm run build both pass" — this referred to the agent's execution environment, not the developer's local machine. `node_modules/` is gitignored and was never present locally.

### Fix

Run `npm install` in `frontend/` before any build or dev command on a fresh checkout.

### Consequences

- Any new machine or fresh clone must run `npm install` in `frontend/` before `npm run build`
- C03's "Done When" criteria should be read as: "passes in the build environment" — local setup requires `npm install` first
- README.md quick-start should include `cd frontend && npm install` as a setup step

---

## D14 — Dockerfile CMD: uvicorn Must Be Invoked via uv run

- **Date:** 2026-06-04
- **Decided by:** Observed during C01 Docker validation
- **Context:** `docker-compose up` failed: `exec: "uvicorn": executable file not found in $PATH` in the backend container.

### Root cause

`uv sync` installs all dependencies — including uvicorn — into a `.venv/` virtual environment inside the container. The `.venv/bin/` directory is not on the system PATH, so `CMD ["uvicorn", ...]` cannot find the executable.

### Fix

Changed `backend/Dockerfile` CMD from:
```
CMD ["uvicorn", "app.main:app", ...]
```
to:
```
CMD ["uv", "run", "uvicorn", "app.main:app", ...]
```

`uv run` activates the virtual environment before executing the command.

### Consequences

- Any executable installed by `uv sync` must be invoked via `uv run <executable>` in Docker CMD/ENTRYPOINT
- This applies to all future Dockerfiles in this project using uv (alembic, pytest, etc.)
- Rex must use `uv run` for any process-launch commands in Docker context

---

## D11 — Agent Commit Blocker: ERAN_COMMIT=1 Bypass Pattern

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (analysis of /insight report), Eran (approval)
- **Context:** /insight report (5 sessions, 47 messages): 9 dissatisfied moments, 1 happy. Primary violations: Aria committed without approval, governance docs updated partially, encoding fix missed a file and blocked Eran's next commit.

### Root cause

Protocol rules live in files. Files don't enforce themselves. Between session resets, Claude loses working context of stored preferences — the same violations recur because the enforcement layer was trust-based, not mechanical.

### Decisions made

**1. hooks/block_agent_commit.py — PreToolUse hook on Bash**
Intercepts bash commands containing git commit, git push, git merge, git rebase. Blocks with exit 2. Eran bypasses with ERAN_COMMIT=1 git commit. Agents never set this env var — blocked mechanically.

**2. CLAUDE.md Critical Rules callout at the very top**
Four rules added before the boot sequence — first thing read every session:
- Always address Eran by name
- Never commit without Eran's explicit approval
- When updating any governance file, update all related files in the same pass (grep to verify)
- Before staging, verify domain ownership

**3. Governance sync check added to pre-commit-doc-checklist skill**
Related file map defined — editing one governance file triggers a check of all related files. Must reach "Governance sync: CLEAN" before approval is surfaced.

**4. Root-cause discipline**
If a fix fails once, stop patching symptoms. State the root-cause hypothesis explicitly before trying another approach.

### Consequences

- Aria-style unauthorized commits are mechanically impossible
- Eran commits freely: ERAN_COMMIT=1 git commit -m "..."
- Partial governance updates caught by skill sync check before approval surfaces
- Same enforcement exists in CLAUDE.md (read every session) + hook (runs every commit)

---

## D15 — Sage Gate C04: Two Findings Dismissed, Two Deferred to C04b

- **Date:** 2026-06-04
- **Decided by:** Claude (gate analysis), Eran (approval)
- **Context:** Sage returned BLOCKING on C04 with 2 CRITICAL and 2 HIGH findings. Claude assessed each against Sage's identity-file blocking criteria before surfacing.

### Findings assessed

| # | Sage severity | Finding | Verdict |
|---|---|---|---|
| 1 | CRITICAL | `SECRET_KEY` needs minimum-length validator | Deferred to C04b — valid defense-in-depth, overstated severity |
| 2 | CRITICAL | `OPENAI_API_KEY: str = ""` is a "plaintext credential" | **Dismissed** — empty string is not a secret; Sage's own rule requires "secrets committed to code" |
| 3 | HIGH | `create_access_token(data: dict)` should accept typed params | **Dismissed** — contradicts C04 spec and C08/C09 handoff contracts; internal callers only |
| 4 | HIGH | `decode_token` needs warning log on JWTError | Deferred to C04b — valid forensics improvement |

### Decision

Insert C04b (`config-security-hardening`) immediately after C04. Rex adds a `SECRET_KEY` minimum-length validator and a structlog warning in `decode_token`. C04 commits as-is; C04b follows before C05 begins.

### Consequences

- C04b is a new row in commit-protocol.md between C04 and C05
- Future Sage invocations on these files should not re-flag findings 2 or 3
- `SECRET_KEY` now fails fast at startup with a clear error message if weak
- `decode_token` failures emit structured logs without leaking details to callers

---

## D16 — JWT Library: PyJWT replaces python-jose

- **Date:** 2026-06-04
- **Decided by:** Eran
- **Context:** During C04 review, Eran noted `python-jose` has had periods of slow maintenance.

### Decision

Replace `python-jose[cryptography]` with `PyJWT>=2.8.0` in `pyproject.toml`.
Update `security.py` imports: `from jwt.exceptions import InvalidTokenError` instead of `from jose import JWTError, jwt`.

### Rationale

`PyJWT` is more actively maintained, has a cleaner API, and is the more common choice in greenfield Python projects post-2023. The interface change is a two-line import swap — no behaviour changes.

### Consequences

- `pyproject.toml`: `python-jose[cryptography]>=3.3.0` → `PyJWT>=2.8.0`
- `security.py`: `JWTError` → `InvalidTokenError`; `jwt` module is now the top-level `jwt` package
- `uv sync` must be re-run after this change to update the lockfile
- No other files reference `jose` — change is fully contained in `security.py`

---

## D17 — PolicyChunk IVFFlat Index Deferred to Alembic Migration

- **Date:** 2026-06-05
- **Decided by:** Rex (C06 execution)
- **Context:** `PolicyChunk.embedding` (Vector 1536) requires an IVFFlat index with pgvector-specific DDL (`USING ivfflat (embedding vector_cosine_ops)`). This cannot be expressed as a standard SQLAlchemy `Index` object.

### Decision

Leave `PolicyChunk.__table_args__` as an empty dict tuple in C06. The IVFFlat index will be created in C07 via `op.execute("CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) ...")` in the Alembic migration.

### Rationale

SQLAlchemy's `Index` constructor does not support pgvector-specific index methods. The correct pattern for pgvector indexes is to define them in the migration, not the model.

### Consequences

- `PolicyChunk` in C06 has no index on `embedding` — correct until C07 runs
- C07 Alembic migration must include `op.execute(...)` for this index explicitly
- Rex (C07) handed off via worklog

---

## D18 — Alembic Must Run Inside Docker Container (Windows Postgres Conflict)

- **Date:** 2026-06-05
- **Decided by:** Rex (C07 execution)
- **Context:** A native Windows Postgres instance unrelated to this project is bound to `localhost:5432`. When `uv run alembic upgrade head` runs from the host, asyncpg connects to the native Windows instance and receives auth failures.

### Decision

All Alembic commands (and any asyncpg operations) must run inside the Docker backend container, which connects to the `db` service by hostname rather than localhost:

```
docker-compose run --rm --no-deps backend sh -c "cd /app && uv run alembic upgrade head"
```

This bypasses the port conflict entirely.

### Consequences

- C08 seed script and all future migration commands must use this invocation pattern
- `alembic.ini` `sqlalchemy.url` placeholder is irrelevant — `DATABASE_URL` env var injected by Docker overrides it
- CI/CD must also run Alembic inside the container, not the host

---

## D19 — JWT Auth: Accepted TOCTOU Trade-off on User State

- **Date:** 2026-06-05
- **Decided by:** Eran (approval), Claude (gate triage of Sage C09 Finding #2)
- **Context:** Sage flagged that `get_current_user` fetches user state (is_active, role) from the DB once at request entry, but a concurrent admin operation could deactivate or demote the user between token issuance and the next request.

### Decision

Accept the standard stateless JWT trade-off: user state is checked once per request against the DB, but the JWT is not revoked on deactivation. A deactivated user's existing tokens remain valid until they expire (governed by `ACCESS_TOKEN_EXPIRE_MINUTES`).

### Why

Re-fetching user state per operation (serializable transactions, re-verify after every ORM action) adds complexity and latency with minimal practical security gain at this scale. The short token TTL (default 30 min) bounds the exposure window.

### Consequences

- Admin revocation is "eventually consistent" — takes effect within one token TTL window
- If immediate revocation is required in a future phase, add a token denylist (Redis or DB table)
- All route implementations (C10–C14) rely on this pattern without modification

---

## D20 — Viktor BLOCK Dismissed: Timing Trade-off on Inactive User Check (C10)

- **Date:** 2026-06-05
- **Decided by:** Eran (Option A approval), Claude (gate triage)
- **Context:** Viktor's C10 gate raised a BLOCK on `auth.py:18` — combining `not user or not user.is_active` in one condition means an inactive user exits before bcrypt runs, creating a timing difference versus "wrong password" (which runs bcrypt). Sage reviewed the same class of issue and rated it WARN, not BLOCK.

### Decision

Dismiss Viktor's BLOCK. Sage (dedicated security reviewer) supersedes Viktor on security severity classification. Accept the timing trade-off and queue for future hardening.

### Why

Viktor's proposed fix rearranges the inactive-user check to after `verify_password`, closing the "inactive vs. wrong-password" timing gap. But it does not address the broader "user not found vs. wrong password" timing gap (Sage Finding #1, also WARN). Neither Viktor's fix nor the current code is fully constant-time. Sage's explicit WARN classification — "timing enumeration is a known trade-off in most auth implementations, addressable in a future hardening pass" — makes the BLOCK an over-escalation.

### Consequences

- Current `auth.py` logic remains: `not user or not user.is_active` → early 401, then `verify_password` → 401
- Timing side-channel acknowledged: email-not-found and inactive paths skip bcrypt; wrong-password path runs it
- Future hardening (post-Phase 1): add constant-time dummy verify for all failure paths
- Sage C09 Finding #1 CLOSED — login route issues tokens only from verified, active users

---

## D22 — Admin User Creation: Unrestricted Role Assignment (Viktor C15 Finding 2)

- **Date:** 2026-06-05
- **Decided by:** Pending — flagged at C15 Viktor batch wave, not yet resolved
- **Context:** Viktor flagged (WARN) that `create_user` in `admin.py` accepts any role including `"admin"` with no secondary confirmation or audit log. An admin can create new admins in one step.

### Finding

Viktor Finding 2 (C11 batch wave, C15 wave): `UserCreate.role` accepts `"admin"` freely. No friction, no escalation check, no audit event.

### Status: OPEN

Not addressed in C15a (which fixes the field-discard and self-demotion bugs). Whether unrestricted admin-creation is acceptable depends on product requirements:
- **Option A (accept):** This is an internal tool. The admin user set is small and controlled. Document it and move on.
- **Option B (restrict):** Require a separate permission level or emit an audit log entry when an admin-role user is created.

Eran to decide before C19 (placeholder pages) when admin UI is first rendered.

---

## D23 — Axios Interceptors: useAuthStore.getState() Instead of Hook

- **Date:** 2026-06-06
- **Decided by:** Aria (C17 execution)
- **Context:** `api/client.ts` Axios interceptors need to read the auth token and call `logout()`. Interceptors are registered once at module initialization and execute outside the React component tree.

### Decision

Use `useAuthStore.getState()` inside the Axios request and response interceptors, not `useAuthStore()` (the React hook).

### Rationale

React hooks (`useAuthStore()`) can only be called inside React components or custom hooks — using them in module-level code throws an invariant violation. Zustand's `.getState()` is the correct API for accessing store state outside of React's rendering lifecycle. The interceptor always reads the current token at request time (not at module load time), so no stale-closure issue exists.

### Consequences

- Any non-React code that needs Zustand state must use `.getState()`, not the hook
- The interceptor pattern is idiomatic Zustand — safe and documented
- C20 login page uses the hook normally (`useAuthStore()`) since it runs inside a component

---

*This document records decisions as they are made. Update it before every Team Lead approval prompt when a non-obvious choice was made.*
