# ORCHESTRATION.md — Manifesto

> The master rules for running this project through the multi-agent workflow.
> CLAUDE.md is the boot sequence. This file is the full ruleset.
> When CLAUDE.md is ambiguous — this file is authoritative.
> Last updated: 2026-06-06

---

## 1. Philosophy

### What this system is

A team of specialized AI agents, each with deep expertise in their domain,
operating under strict discipline: one commit per concern, one owner per file,
and Eran — the Team Lead — who approves every change before it lands.

Claude is the orchestrator. Claude never writes application code. Claude routes
context, sequences handoffs, and makes sure every agent has exactly the
information they need — no more, no less.

### Three pillars

**Domain ownership is absolute.** Each agent owns a set of files. They never
touch anything outside that set. When they find a problem outside their domain,
they log it and flag it — they do not fix it. This prevents one agent's change
from silently breaking another agent's assumptions.

**Commit discipline is non-negotiable.** One commit per protocol step. One owner
per commit. Eran approves before every commit lands. This makes the system
auditable, reversible, and safe to run over long sessions.

**Context efficiency is engineered, not hoped for.** Token budgets are defined
per agent. Every invocation loads the minimum context needed. The system stays
fast and accurate across 21 commits as well as it does across 3.

---

## 2. The Commit Loop

Every commit follows this exact sequence. No step is skipped.

```
STEP 1 — Claude reads commit-protocol.md
└── Identifies step number, name, assignee, and testing gate

STEP 2 — Claude reads project-state.json
└── Checks for open blockers. Blocker exists → surface to Eran and stop.

STEP 3 — Claude builds the live context package for the owning agent
└── Runs hooks/prepare_agent_delegation.py for the active commit and owner
    Refreshes the cached graph only when stale
    Produces a bounded brief: primary files, contracts, dependencies, hubs, tests,
    boundaries, handoffs, acceptance criteria, and expansion triggers

STEP 3.5 — Claude presents the Commit Preview to Eran
└── Structured card: what, why now, files to touch, test gates
    Asks: "Invoke [Agent] to begin?"
    Eran must respond with explicit approval before Step 4 runs.

STEP 4 — Pre-invocation check (mandatory)
└── "Do I already know the exact file, line, and content to change?"
    YES → use Edit directly. Do NOT invoke an agent.
          Agent overhead = 10–30k tokens. Edit = ~200 tokens.
    NO  → invoke the agent with the generated delegation brief verbatim.

STEP 5 — Agent executes
└── Writes worklog continuously. Decisions logged as made.

STEP 6 — Agent completes
└── Updates Current State Header. Writes outgoing handoff notes.

STEP 7 — Test gate
└── Tests pass → continue.
    Tests fail → return to agent. Agent fixes. Back to Step 5.
    Gate does not surface to Eran until tests pass.

STEP 8 — Quality gate wave (parallel where triggered)
└── Viktor: every 5th commit (C05, C10, C15, C20) — Haiku
    Sage:   conditional (auth, secrets, user input) — Haiku
    Mira:   conditional (user-facing behavior) — Haiku

    Blocking finding → owning agent fixes in a NEW commit (no gate-fix passes)
    Viktor Hard Block → routes directly to Eran

STEP 9 — Pre-commit documentation checklist (Claude)
└── DECISIONS.md — non-obvious choice or debate made?
    ARCHITECTURE.md — new component or data flow introduced?
    GLOSSARY.md — new term introduced?
    TOKEN_RECORDS.md — always: add commit entry

STEP 10 — Eran's approval
└── Approval prompt: what was built, test results, gate findings, "Approve to commit?"

STEP 11 — Claude commits on Eran's behalf
└── export ERAN_COMMIT=1 && git commit -F <msg_file>
    pre_commit_check.py runs (domain boundary, message format)
    Commit message must include "Commit #NN" on its own line.

STEP 12 — verify_constraints + post-commit doc sweep (mandatory)
└── python hooks/verify_constraints.py --commit NN --agent NAME --tokens N
    Writes CONSTRAINT_LOG.md and constraint-dashboard.html.

    Then immediately: stage and commit ALL protocol files as a chore:
      project-state.json, commit-protocol.md, TOKEN_RECORDS.md,
      CONSTRAINT_LOG.md, constraint-dashboard.html,
      .claude/agents/logs/<agent>-worklog.md,
      backend/DOMAIN_MAP.md, frontend/DOMAIN_MAP.md,
      ARCHITECTURE.md and GLOSSARY.md (if updated this commit)
    Commit: chore(state): advance state after C-NN

    Final check: git status must show no modified or untracked files
    in protocol-managed paths. If any remain — commit them before Step 13.
    BLOCKED: Do not proceed to Step 13 until git status is clean.

STEP 13 — Claude presents next Commit Preview
└── Eran approves → loop restarts at Step 1
    Eran defers → Claude holds. No agent invoked until approval.
```

---

## 3. The Context Budget System

### Context Pyramid

```
TIER 0 — Always loaded (~4K tokens):
├── Agent identity file (.claude/agents/[name].md)
└── Current State Header from worklog (≤50 lines)

TIER 1 — Task context (~3K tokens, per invocation):
├── Active commit spec (commit-specs/commit-XX.md)
├── Relevant handoff notes
└── project-state.json blockers section

TIER 2 — Historical depth (~4K tokens, only when needed):
├── Most recent 2 worklog sessions
└── Specific DECISIONS.md entries referenced in the task

TIER 3 — Archive (only on explicit request):
└── Archived worklog sessions
```

Claude does not load Tier 2 by default. If the task does not explicitly require
historical depth, Tier 0 + Tier 1 is the entire context package.

### Live selection and expansion

The commit specification remains authoritative, but file selection is produced by
`hooks/prepare_agent_delegation.py`. The context engine adds only bounded structural
evidence: direct dependencies and callers, explicit cross-domain contracts, tests, and
at most the configured nearby domain hubs.

Agents do not scan folders. They read selected files first. Expansion is permitted only
for unresolved symbols, missing contracts, failing tests, or contradictory implementation
evidence. Every expansion states its reason, exact query/path, expected decision, and
tradeoff before the tool call, then records the result in the worklog.

### Token budget targets

| Agent type | Target per invocation |
|---|---|
| Implementor (Rex, Adam, Aria) | ≤60k tokens |
| Reviewer (Viktor, Sage, Mira) | ≤15k tokens |

When a session approaches 80% of context capacity:
1. Trigger `/archive-worklog` for any agent with >3 completed sessions
2. Compress context packages to Tier 0 + Tier 1 only
3. Alert Eran that compression has occurred

---

## 4. Quality Gate Rules

### Viktor — every 5th commit, Haiku

Batch review across all diffs since the last wave. Token target: ≤20k per wave.

**Blocks immediately (system-breaking only):**
- Import errors preventing app startup
- Unhandled exceptions on the happy path
- Async/sync mixing that blocks the event loop
- SQL injection, exposed secrets, auth bypass
- Missing required arguments causing TypeError at runtime

**Logged for deferred review (everything else):**
- Dead code, unused variables, style issues
- Missing type annotations
- Performance concerns (unless O(n²) on unbounded input)

### Sage — conditional, Haiku

Triggers when a commit touches: auth, JWT, secrets, env vars, user input, file uploads, external API calls.

**Blocks immediately:** Secrets in code, SQL injection, auth bypass, critical CVE-level issues.
**Logged:** LOW/MEDIUM findings, non-critical information disclosure.

### Mira — conditional, Haiku

Triggers on user-facing behavior changes. All findings are advisory — never blocks.

### No gate-fix passes

A blocking finding from any reviewer becomes its own next commit in the sequence.
The gate does not re-run in the same loop. Claude does not re-invoke the agent to fix and re-review.

---

## 5. Cross-Agent Communication

All agent-to-agent communication routes through Claude. No direct contact.

**Handoff format:**
```
## Handoff → [Agent]
From: [Agent] · Commit [N] `[name]` complete.
What I built: [one paragraph]
What you need to know: [interfaces, env vars, constraints]
Files to read: [list]
```

**Cross-domain finding:**
```
🐛 CROSS-DOMAIN FINDING → [Agent]
Found by: [Agent] during Commit [N]
File: [path:line]
Problem: [description]
Impact: [what breaks]
Suggested fix: [direction only — I will not touch this file]
```

---

## 6. Rollback Protocol

Rollbacks are revert commits — never force-pushes. History is never rewritten.

Before any git command: Claude assesses blast radius and surfaces to Eran.
Eran confirms blast radius before rollback proceeds.

After rollback:
1. Mark reverted commits as `⏪ reverted · [date]` in commit-protocol.md
2. Update project-state.json
3. Notify affected agents via worklog entries
4. Ask Eran: "Should the plan remain the same, or does this require a /replan?"

---

## 7. Replanning Protocol

When a discovery, changed requirement, or rollback invalidates part of the plan:

1. Claude drafts proposed changes to commit-protocol.md
2. Shows: what is removed, added, or reordered — and why
3. Surfaces to Eran with one-paragraph rationale
4. Eran approves or modifies
5. Claude updates commit-protocol.md and project-state.json
6. Claude notifies all agents whose upcoming work is affected

The commit index can only change with Eran's approval.
No agent can propose a replan that expands their own domain scope.

---

## 8. Slash Commands

| Command | What it does |
|---|---|
| `/status` | Full project status: commit progress, active step, open handoffs, blockers |
| `/next-step` | Identifies next pending commit, checks prerequisites, asks for approval |
| `/handoff-check` | Verifies all required handoffs are in place for the next step |
| `/rollback` | Blast radius assessment → revert commit → state update → agent notification |
| `/replan` | Formally revises the commit index: draft → Eran approval → apply |
| `/review-request` | Ad-hoc Viktor review outside the commit loop |
| `/security-audit` | Ad-hoc Sage review of specified files |
| `/archive-worklog` | Archives old worklog sessions to keep context lean |
| `/project-complete` | Final gate, handoff doc, project completion |

---

## 9. Non-Negotiables

These cannot be overridden by any agent or any instruction:

1. One commit per protocol step — no combining
2. Eran approves the Commit Preview before any agent is invoked — no exceptions
3. Eran approves the commit after quality gates — no exceptions
4. Tests pass before approval surfaces — no bypassing the gate
5. Viktor reviews every 5th commit — no skipping
6. No agent touches another's domain — findings are routed, not fixed in place
7. Worklogs are written in real time — not reconstructed after the fact
8. Secrets never appear in code — not in defaults, not in comments
9. Scope overflows are flagged immediately — not silently built
10. Never spawn an agent when the exact file, line, and content is already known — use Edit
