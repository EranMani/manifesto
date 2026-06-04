# team-preferences.md — Manifesto

> Claude reads this file at every session boot, immediately after project-state.json.
> These preferences tune agent behavior for this project and Team Lead.
> Last updated: 2026-06-04

---

## Project Context

```
Project name:      manifesto
Team Lead:         Eran Mani
Phase:             greenfield — Phase 1 (core inventory, no AI)
Deadline pressure: none (quality over speed)
Public-facing:     internal tool (future AWS deployment)
```

---

## Core Rules (non-negotiable — read before every commit)

```
1. NO GATE-FIX PASSES. EVER.
   If Viktor or Sage blocks → surface to Eran → fix is its own next commit.
   Do NOT re-invoke the agent and re-run the gate in the same loop.

2. ALWAYS SPECIFY model: "haiku" FOR REVIEWER AGENTS.
   Viktor, Sage, Mira → model: "haiku" — no exceptions.
   Omitting it runs on Sonnet (3× cost).

3. VALIDATE THE SPEC BEFORE INVOKING ANY AGENT.
   Does the spec actually achieve the stated goal?
   A rejected agent pass costs the same tokens as a successful one.

4. NEVER SPAWN AN AGENT FOR A KNOWN EDIT.
   If the exact file, line, and new content are already known → use Edit directly.
   Agent overhead = 10–30k tokens. Edit = ~200 tokens.

5. DEBATES AND DECISIONS GO INTO DECISIONS.md IMMEDIATELY.
   Eran reads DECISIONS.md to build his understanding of the process.
   Every non-obvious choice and every Andrej/Boris debate gets recorded there.
```

---

## Viktor — Code Review Calibration

```
Trigger:    batch wave every 5 commits (C05, C10, C15, C20)
Model:      haiku — always
```

| Concern type | Behavior | Notes |
|---|---|---|
| Async/sync mixing | block | FastAPI async routes must not call sync SQLAlchemy |
| Type discipline | concern | strict on all new code |
| Error handling | concern | public-facing app |
| Unguarded input | block | any route that accepts user input without validation |
| Style / formatting | comment | advisory only |
| Performance | concern | flag O(n²) on unbounded input |

**How Claude passes context to Viktor:**
- Always pass a `git diff` — never paste full file contents
- Prompt under 200 words before the diff
- Viktor uses Read with line ranges for targeted inspection only

---

## Sage — Security Calibration

```
Trigger:    conditional — auth, secrets, user input, external API calls
Model:      haiku — always
```

| Finding level | Behavior |
|---|---|
| CRITICAL | hard block — always |
| HIGH | block |
| MEDIUM | flag — bundle into approval prompt |
| LOW | bundle into approval prompt |

**Manifesto-specific rules:**
- JWT secret: flag any commit where `SECRET_KEY` could reach production as "changeme"
- Login route: must never reveal which field (email vs password) failed — generic 401 only
- `added_by` field: must come from authenticated user, never from request body
- Admin routes: must be guarded by `require_role("admin")` — verify after any auth refactor

---

## Mira — Product Calibration

```
Trigger:    conditional — user-facing behavior changes only
Model:      haiku — always
```

Invoke Mira when: new routes with user-visible output, UI pages with real content, API shape changes.
Skip Mira on: stubs, placeholders, infra, migration, seed, smoke test.

---

## Model Assignments

```
Haiku  (fast, low cost):   Viktor, Sage, Mira — all reviewers
Sonnet (default):          Rex, Adam, Aria — all implementors
Opus   (never):            Banned — too expensive for any use
```

---

## Universal Tool Use Cap — All Agents

**25 tool uses maximum per agent invocation. No exceptions.**

If an agent hits 25 and is not done, it stops and reports. Claude does not re-invoke to continue.

---

## Execution Constraints — Include Verbatim in Every Invocation

### Implementors (Rex, Adam, Aria)

```
EXECUTION CONSTRAINTS:
- Max tool uses: 25. Plan reads upfront. Batch writes. Hit 25 → stop and report.
- Two phases only: Phase 1 — all reads. Phase 2 — all writes. No reads in Phase 2.
- Do not re-read any file already read this session.
- Worklog: one write at task completion only.
- Test runs: maximum 2. On second failure, report and stop.
- Code comments: one line max, functional only.
```

### Reviewers (Viktor, Sage)

```
EXECUTION CONSTRAINTS:
- Max tool uses: 25. Work from the diff. Do NOT read files speculatively.
- Only Read a file if a specific diff line is ambiguous — max 15 lines per targeted read.
```

### Mira

```
EXECUTION CONSTRAINTS:
- Max tool uses: 5. Do not read any files — assess from Claude's brief only.
```

---

## Quality Gate Trigger Matrix

| Commit type | Viktor | Sage | Mira |
|---|---|---|---|
| Infrastructure only | every 5th | skip | skip |
| Config / env / secrets | every 5th | **run** | skip |
| Auth, JWT, password | every 5th | **run** | skip |
| New route with user input | every 5th | **run** | **run** |
| New service / business logic | every 5th | conditional | conditional |
| Frontend — no user data | every 5th | skip | **run** |
| Frontend — renders user data | every 5th | **run** | **run** |
| Stub / placeholder only | skip | skip | skip |
| Smoke test commit | skip | skip | skip |

---

## Context Window Management

```
After every commit:     /clear — all state is in project files, nothing is lost
Mid-commit at ~60k:     /compact — preserves in-flight work
```

---

## Commit Preview Format (locked 2026-06-04)

Every Commit Preview must follow this exact structure — no variations:

```
## Commit [N] — `[name]` · [Assignee]

**Summary:** [1-2 sentences plain English. Junior-readable. What it does and why it matters.
             This replaces the old "What" field — do not use "What".]
**Why now:** [one sentence — sequencing rationale]

**⚡ Parallel:** [only if applicable — omit this line entirely if no parallelism]

**Changes:**
- `path/to/file` — new/update/delete: [what, in 5 words]

**Test gates:** [gate 1] · [gate 2] · [gate 3]

**Quality gate:** [always state explicitly — e.g. "Viktor batch wave at C05. No per-commit gate — infrastructure only."
                  Never write "None" — always explain which rule applies and why no gate triggers.]

Invoke [Agent] to begin?
```

**Why this format (debate 2026-06-04):**
- "Summary" replaces "What" — same token cost, but junior-readable. Eran should be able to understand any commit without reconstructing it from the file list.
- "What" and "Summary" conveyed identical information — one field does both jobs.
- Parallel callout moved above Changes — it's an approval-time decision, not a footnote.
- Quality gate is always explicit — "None" implied the check was skipped; the rule statement shows the system is working as designed.

---

## Communication Preferences

```
Tone:                   Direct. Lead with what decision Eran needs to make.
Approval prompt:        Summary → test results → gate findings → "Approve to commit?"
Escalation threshold:   Low — escalate early rather than resolve autonomously
Address Team Lead as:   "Eran" always
```

---

## Commit Message Format (required for post-commit hook)

```
[conventional-commit subject line]

[body — what and why]

Commit #NN
-- AgentName
```

The post-commit hook parses `Commit #NN` to auto-update commit-protocol.md and project-state.json.

---

## Viktor Pre-Brief (include in every implementor invocation)

```
Viktor will check:
- All collection types explicitly typed (list[X], not bare list)
- All finite string fields use Literal[...], not str
- All routes are async — no sync SQLAlchemy calls
- Pydantic schemas for all route inputs/outputs
- No secrets in staged files
```

Add commit-specific items where the spec has known sharp edges.

---

## Change Log

| Date | Change | Reason |
|---|---|---|
| 2026-06-04 | Initial creation | Project initialized |
