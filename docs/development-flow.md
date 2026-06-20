# Development Flow — Ask, Forge, Execute

This document describes the complete development workflow powered by three
commands: `/ask`, `/forge`, and `/next-step`. Together they form a pipeline
that goes from "I have a question" to "the code is committed."

## Table of Contents

- [Command Quick Reference](#command-quick-reference)
  - [/ask — Understand](#ask--understand)
  - [/forge — Plan](#forge--plan)
  - [/next-step — Execute](#next-step--execute)
  - [Common Pipelines](#common-pipelines)
- [The Flow at a Glance](#the-flow-at-a-glance)
- [Stage 1 — Understand (/ask)](#stage-1--understand-ask)
- [Stage 2 — Plan (/forge)](#stage-2--plan-forge)
- [Stage 3 — Execute (/next-step)](#stage-3--execute-next-step)
- [The Handoffs](#the-handoffs)
- [Complete Walkthrough](#complete-walkthrough)
- [Interview Mode — The Training Loop](#interview-mode--the-training-loop)
- [System Architecture](#system-architecture)
  - [File Map](#file-map)
  - [Data Flow](#data-flow)
  - [Agent Roster](#agent-roster)
  - [Hook Pipeline](#hook-pipeline)
- [Installing in a New Project](#installing-in-a-new-project)
  - [Prerequisites](#prerequisites)
  - [Step 1 — Copy the Command Files](#step-1--copy-the-command-files)
  - [Step 2 — Copy the Persona Profiles](#step-2--copy-the-persona-profiles)
  - [Step 3 — Set Up the Hooks](#step-3--set-up-the-hooks)
  - [Step 4 — Create the Protocol Files](#step-4--create-the-protocol-files)
  - [Step 5 — Configure Agent Domains](#step-5--configure-agent-domains)
  - [Step 6 — Adapt Personas](#step-6--adapt-personas)
  - [Step 7 — Run the Codebase Scan](#step-7--run-the-codebase-scan)
  - [Step 8 — Verify the Installation](#step-8--verify-the-installation)
  - [What to Customize](#what-to-customize)
  - [What Works Out of the Box](#what-works-out-of-the-box)
- [Design Decisions](#design-decisions)

---

## Command Quick Reference

Everything you can type, in one place.

### /ask — Understand

```bash
# ─── Ask a question ───────────────────────────────────────────────
/ask how does auth work?                          # default (engineer persona)
/ask founder what can this product do?            # plain English, no jargon
/ask pm what's the state of shipments?            # feature status, gap analysis
/ask eng how does the ingestion pipeline work?    # full technical detail

# ─── Guided discovery (question bank) ─────────────────────────────
/ask questions                     # question bank with default persona
/ask founder questions             # plain-English questions + forge prompts
/ask pm q                          # product questions + forge prompts (shorthand)
/ask eng q                         # technical questions + forge prompts

# ─── Interview mode (system challenges you) ───────────────────────
/ask ie                            # engineering interview, random topics
/ask ip                            # product manager interview
/ask if                            # founder / strategic interview

# ─── Topic-focused interviews ─────────────────────────────────────
/ask ie migration safety           # all 6 challenges about migration safety
/ask ip user onboarding            # all 6 challenges about onboarding
/ask if competitive moats          # all 6 challenges about moats

# ─── Follow-ups (no command needed) ───────────────────────────────
# After any /ask answer, just type a follow-up naturally:
what about vendor management?      # carries forward persona + domain context
```

**Output**: answers, guided questions, forge-ready prompts, interview
scorecards. Read-only — no files modified.

### /forge — Plan

```bash
# ─── Features ─────────────────────────────────────────────────────
/forge add pagination to the shipments endpoint
/forge add document search with keyword highlighting across backend and frontend

# ─── Bug fixes ────────────────────────────────────────────────────
/forge fix the chat scroll regression when messages overflow

# ─── Refactors ────────────────────────────────────────────────────
/forge refactor auth middleware to support session-based tokens

# ─── From /ask "Build next" prompts (paste directly) ──────────────
/forge add shipment editing — PATCH endpoint with role-based access and frontend form
/forge build vendor dashboard UI — frontend for existing vendor CRUD so managers can browse and filter

# ─── From insights ────────────────────────────────────────────────
/forge turn the shipment update gap into a commit spec
```

**Output**: `commit-specs/commit-NN.md` files, updated protocol and
state. No code changes — that's `/next-step`.

### /next-step — Execute

```bash
# ─── Normal mode (safe default) ───────────────────────────────────
/next-step                         # show preflight card, wait for approval

# ─── Auto mode (unattended) ───────────────────────────────────────
/next-step --auto                  # auto-approve clean preflights, loop all commits

# ─── Auto-once (single commit, unattended) ────────────────────────
/next-step --auto --once           # run exactly one commit, then stop
```

**Output**: committed code, advanced project state, token records.

### Common Pipelines

```bash
# ─── Discovery → Build (fastest path) ─────────────────────────────
/ask pm q                          # see gaps + "Build next" prompts
/forge {paste a prompt}            # plan the commits
/next-step --auto                  # execute all commits

# ─── Deep dive → Targeted fix ─────────────────────────────────────
/ask eng how does auth work?       # understand the system
/ask eng what's the attack surface for JWT tokens?  # dig deeper
# (after 5+ questions, /ask suggests forge prompts)
/forge add token refresh with sliding expiration and revocation list
/next-step --auto --once           # execute one commit

# ─── Interview → Learn → Build ────────────────────────────────────
/ask ie auth and security          # 6 engineering challenges
# (scorecard shows weak areas + "Act on this" forge prompts)
/forge add rate limiting and brute-force protection to the login endpoint
/next-step

# ─── Full product audit → Roadmap ─────────────────────────────────
/ask founder q                     # what can this product do?
/ask pm q                          # what features are built vs. missing?
/ask eng q                         # what's the architecture state?
# each shows "Build next" — pick the highest-priority prompt
/forge {paste prompt}
/next-step --auto
```

---

## The Flow at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   /ask                    /forge                  /next-step    │
│                                                                 │
│   "What's the state     "Add pagination        "Execute C80"   │
│    of shipments?"        to shipments"                          │
│                                                                 │
│   ┌──────────┐          ┌──────────┐          ┌──────────┐     │
│   │Understand│ ──────►  │  Plan    │ ──────►  │ Execute  │     │
│   │          │ (forge   │          │          │          │     │
│   │ Persona  │ prompts) │ 6 phases │          │ Preflight│     │
│   │ Tiers    │          │ Scan     │          │ Implement│     │
│   │ Q&A      │          │ Agents   │          │ Verify   │     │
│   │ Interview│          │ Specs    │          │ Commit   │     │
│   │ Build ►  │          │          │          │          │     │
│   └──────────┘          └──────────┘          └──────────┘     │
│                                                                 │
│   Read-only              Creates specs          Creates code    │
│   Forge-ready prompts    Updates protocol       Updates state   │
│   Token-efficient        Validated plan          Verified commits│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stage 1 — Understand (/ask)

**Purpose**: explore the codebase, understand features, identify gaps.

**What it does**:
- Answers questions in the language of the audience (founder, PM, engineer)
- Uses a 3-tier pipeline (Quick/Standard/Deep) to match cost to complexity
- Suggests follow-up questions to guide exploration
- Generates **forge-ready prompts** from codebase gaps — copy-paste to start building
- After 5+ questions in the same domain, suggests specific forge prompts

**Key capability**: the question bank (`/ask pm questions`) generates
contextual questions from the actual codebase state — hub files, open
issues, recent changes — and translates identified gaps into actionable
`/forge` prompts in the "Build next" section. This gives one person
wearing multiple hats an entry point without needing to know what to ask
*or* how to phrase the build task.

**Output**: understanding + actionable forge prompts. No files are
created or modified.

**Detailed docs**: [docs/ask-command.md](ask-command.md)

---

## Stage 2 — Plan (/forge)

**Purpose**: turn a task description into a validated commit plan.

**What it does**:
1. Analyzes the task intent (feature/fix/refactor, domains, scope)
2. Scans the codebase for target files, hubs, and ownership
3. Consults domain agents for design input (not implementation)
4. **Challenges the design** — cross-examines agent recommendations for
   architecture flaws, performance gaps, security holes, UX problems,
   and missing edge cases before writing specs
5. Decomposes into atomic commits with dependency ordering
6. Generates full specs (14 required sections each)
7. Validates every spec against the protocol

**Key capability**: design challenge phase. Before specs are written,
Claude cross-examines every agent recommendation with domain-appropriate
challenges (backend tasks get architecture/performance/security challenges,
frontend tasks get UX/product-impact challenges, AI tasks get retrieval-quality/
hallucination challenges). Weaknesses are caught and revised before they
become committed code — the most expensive place to fix them.

**Output**: `commit-specs/commit-NN.md` files, updated `commit-protocol.md`,
updated `project-state.json`.

**Detailed docs**: [docs/forge-command.md](forge-command.md)

---

## Stage 3 — Execute (/next-step)

**Purpose**: execute the plan one commit at a time.

**What it does**:
1. Reads the next pending commit from the protocol
2. Runs a preflight check (dependencies, ownership, spec validity)
3. Shows a compact approval card
4. After approval: implements, verifies, finalizes, commits
5. Advances state (project-state.json, commit-protocol.md, TOKEN_RECORDS.md)
6. In auto mode: loops through all pending commits

**Key capability**: auto mode (`--auto`) can execute an entire commit
sequence unattended — auto-approving clean preflights, auto-committing
verified implementations, and auto-advancing state. It stops safely on
any failure, blocked preflight, or user interruption.

**Output**: committed code, advanced project state.

**Detailed docs**: [docs/next-step-command.md](next-step-command.md)

---

## The Handoffs

### /ask → /forge

The handoff from understanding to planning happens in three ways:

**Direct from question bank**: the "Build next" section generates
forge-ready prompts alongside the questions. The user pastes one:
```bash
# Question bank showed this in "Build next":
/forge add shipment editing — PATCH endpoint with role-based access and frontend form
```

**From deep exploration**: after 5+ questions in the same domain, `/ask`
generates specific forge prompts from the conversation context:
```
You're going deep on shipments. Ready to build?

  /forge add shipment editing — PATCH endpoint with role-based access and frontend form
  /forge add shipment list filtering — status and vendor filters with pagination
```

**Manual**: the user writes their own forge command based on what they learned:
```bash
/forge add update endpoint for shipments
```

**From interview sessions**: after a session scorecard, the "Act on this"
section suggests forge prompts derived from weaknesses the session exposed.

### /forge → /next-step

The handoff from planning to execution is direct:

```
FORGE COMPLETE — add pagination to shipments
...
Ready for /next-step execution.
```

The user runs `/next-step` and the first pending commit's preflight appears.

### /next-step → /next-step (auto loop)

In auto mode, each completed commit loops back to the next pending commit:

```
✓ C80 committed. Starting C81...
```

### /next-step → /ask (feedback loop)

After implementation is complete, the user can return to `/ask` to verify
what was built, identify new gaps, and start the cycle again.

---

## Complete Walkthrough

Here's the full flow for adding pagination to the shipments endpoint:

### 1. Discover gaps with guided questions

```bash
/ask pm q
```

The question bank shows contextual questions plus a "Build next" section:

```
BUILD NEXT — paste any of these into the chat to start planning:

  /forge add shipment editing — PATCH endpoint with role-based access so managers can update shipments after creation
  /forge build shipment list UI — frontend for existing shipment CRUD so managers can browse and filter
  /forge add pagination and filtering to the shipments list endpoint
```

### 2. Optionally dig deeper

```bash
/ask eng how does the shipments endpoint handle large datasets?
```

Output reveals: `list_shipments()` returns `select(Shipment)` with no
limit — every row, every time. With growing data, this becomes a
performance problem.

### 3. Paste a forge prompt or write your own

```bash
# Paste directly from "Build next":
/forge add pagination and filtering to the shipments list endpoint
```

Forge runs:
- Intent: feature, backend domain, keywords: shipments, pagination, filtering
- Scan: identifies `shipments.py`, `shipment.py`, schema files, test files
- Agent input: Rex recommends limit/offset with cursor-based fallback
- Decomposition: C80 (pagination) → C81 (filtering), both Rex-owned
- Specs generated, validated, protocol updated

### 4. Execute the plan

```bash
/next-step --auto
```

Auto mode:
- C80 preflight: READY → auto-approved
- Implements pagination in `shipments.py` and `shipment.py`
- Runs tests → pass
- Commits: `feat(shipments): add pagination to list endpoint`
- State advanced
- C81 preflight: READY → auto-approved
- Implements filtering
- Runs tests → pass
- Commits: `feat(shipments): add status and vendor filtering`
- No more pending commits → stops

### 5. Verify the result

```bash
/ask pm what's the state of shipments now?
```

Updated gap analysis shows pagination and filtering as "Built."

---

## Interview Mode — The Training Loop

The `/ask` command includes an interview mode that exists outside the
development flow. It's a training tool:

```
/ask ie                    ← engineering interview (random topics)
/ask ip                    ← product manager interview
/ask if                    ← founder interview
/ask ie auth and security  ← focused on specific topics
```

Interview sessions are 6 challenges each, grounded in the actual codebase.
At the end, a scorecard identifies strengths and areas to develop, with a
copy-pasteable command to start the next focused session and optional
forge prompts to act on weaknesses the session exposed.

```
Recommended next session:
  Focus on migration safety and test isolation.
  Run: /ask ie migration safety and test isolation

Act on this:
  /forge add rate limiting and brute-force protection to the login endpoint
  /forge add database migration safety checks with rollback tests
```

This creates two loops: a **learning loop** (interview → scorecard →
focused session) and a **build loop** (interview → forge prompt →
commit). The same session that builds your thinking also surfaces
concrete work to strengthen the codebase.

---

## System Architecture

### File Map

```
.claude/
├── commands/
│   ├── ask.md                    ← /ask command definition
│   ├── forge.md                  ← /forge command definition
│   └── next-step.md              ← /next-step command definition
├── persona-profiles.json         ← Persona definitions (6 personas)
├── stack-profile.json            ← Technology stack anchors per domain
└── settings.json                 ← Claude Code configuration

hooks/
├── forge_scan.py                 ← Codebase scanner (deterministic)
├── forge_planner.py              ← Commit decomposition engine
├── validate_commit_spec.py       ← Spec validation (14 sections)
├── preflight_commit.py           ← Pre-execution readiness check
├── prepare_agent_delegation.py   ← Delegation package builder
├── direct_execution_lifecycle.py ← Claude-direct context prep
├── verify_constraints.py         ← Post-implementation constraints
├── finalize_commit.py            ← Pre-commit finalization
├── pre_commit_check.py           ← Git hook: domain enforcement
├── context_telemetry.py          ← Execution telemetry
├── notify_agent_done.py          ← Email notifications
├── agent-config.json             ← Agent definitions and domains
└── tests/                        ← Hook test suite

commit-specs/
├── TEMPLATE.md                   ← Spec template (14 sections)
├── ISSUE_TO_COMMIT_MAPPING.md    ← Decomposition rules
└── commit-NN.md                  ← Individual commit specs

.forge/
├── report.json                   ← Codebase scan output
└── plan.json                     ← Commit decomposition plan

docs/
├── ask-command.md                ← /ask documentation
├── forge-command.md              ← /forge documentation
├── next-step-command.md          ← /next-step documentation
├── development-flow.md           ← This file
└── project-overview.md           ← Project vision, end goal, how everything connects

project-state.json                ← Project position and state
commit-protocol.md                ← Commit index and status
TOKEN_RECORDS.md                  ← Per-commit token records
DECISIONS.md                      ← Architectural decision log
```

### Data Flow

```
                    ┌──────────────────┐
                    │  User question   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │     /ask         │
                    │                  │
                    │ persona-profiles │──► Answer or Interview
                    │ .forge/report    │──► Forge-ready prompts
                    │ project-state    │
                    └────────┬─────────┘
                             │ (insight + forge prompts)
                    ┌────────▼─────────┐
                    │     /forge       │
                    │                  │
                    │ forge_scan.py    │──► .forge/report.json
                    │ forge_planner.py │──► .forge/plan.json
                    │ agent design     │──► commit-specs/commit-NN.md
                    │ validate_spec.py │──► commit-protocol.md (updated)
                    │                  │──► project-state.json (updated)
                    └────────┬─────────┘
                             │ (validated plan)
                    ┌────────▼─────────┐
                    │   /next-step     │
                    │                  │
                    │ preflight.py     │──► Approval card
                    │ implementation   │──► Code changes
                    │ verify + finalize│──► Constraint artifacts
                    │ git commit       │──► Committed code
                    │ state advance    │──► project-state.json (advanced)
                    │                  │──► commit-protocol.md (done)
                    │                  │──► TOKEN_RECORDS.md (new row)
                    └──────────────────┘
```

### Agent Roster

| Agent | Domain | Role in /ask | Role in /forge | Role in /next-step |
|-------|--------|-------------|---------------|-------------------|
| Rex | Backend | Answers backend Q&A | API/model design input | Implements backend commits |
| Aria | Frontend | Answers frontend Q&A | Component design input | Implements frontend commits |
| Nova | AI/ML | Answers AI Q&A | Pipeline design input | Implements AI commits |
| Adam | DevOps | Answers devops Q&A | Infrastructure design input | Implements devops commits |
| Viktor | Quality | Code review Q&A | — | Post-implementation review |
| Sage | Security | Security review Q&A | — | Security audit |
| Mira | Product | — | UX decisions | — |

### Hook Pipeline

```
/forge                          /next-step
──────                          ──────────
forge_scan.py                   preflight_commit.py
      │                               │
forge_planner.py                direct_execution_lifecycle.py
      │                           OR prepare_agent_delegation.py
validate_commit_spec.py               │
                                [Implementation]
                                      │
                                verify_constraints.py
                                      │
                                finalize_commit.py
                                      │
                                pre_commit_check.py (git hook)
                                      │
                                notify_agent_done.py (auto mode)
```

---

## Installing in a New Project

This section describes how to bring the ask → forge → next-step flow
into a different project.

### Prerequisites

- Claude Code CLI installed and configured
- Python 3.10+ (for hooks)
- Git repository
- `.claude/` directory exists (created by Claude Code)

### Step 1 — Copy the Command Files

```bash
# Create the commands directory if it doesn't exist
mkdir -p .claude/commands

# Copy the three command definitions
cp <source>/manifesto/.claude/commands/ask.md .claude/commands/
cp <source>/manifesto/.claude/commands/forge.md .claude/commands/
cp <source>/manifesto/.claude/commands/next-step.md .claude/commands/
```

### Step 2 — Copy the Persona Profiles

```bash
cp <source>/manifesto/.claude/persona-profiles.json .claude/
```

You'll customize the personas later (Step 6), but the structure works
immediately.

### Step 3 — Set Up the Hooks

The minimum viable hook set for the flow:

```bash
mkdir -p hooks

# Required for /forge
cp <source>/manifesto/hooks/forge_scan.py hooks/
cp <source>/manifesto/hooks/forge_planner.py hooks/

# Required for /next-step
cp <source>/manifesto/hooks/preflight_commit.py hooks/
cp <source>/manifesto/hooks/validate_commit_spec.py hooks/
cp <source>/manifesto/hooks/finalize_commit.py hooks/
cp <source>/manifesto/hooks/pre_commit_check.py hooks/
cp <source>/manifesto/hooks/verify_constraints.py hooks/

# Required for agent routing
cp <source>/manifesto/hooks/agent-config.json hooks/
```

**Optional but recommended:**

```bash
# Telemetry and budget tracking
cp <source>/manifesto/hooks/context_telemetry.py hooks/
cp <source>/manifesto/hooks/claude_budget.py hooks/

# Delegation support
cp <source>/manifesto/hooks/prepare_agent_delegation.py hooks/
cp <source>/manifesto/hooks/direct_execution_lifecycle.py hooks/

# Notifications (for auto mode)
cp <source>/manifesto/hooks/notify_agent_done.py hooks/
```

### Step 4 — Create the Protocol Files

```bash
# Project state (minimal)
cat > project-state.json << 'EOF'
{
  "project": "your-project-name",
  "tldr": "Initial setup. No commits yet.",
  "phase": 1,
  "last_completed_commit": "0",
  "next_commit": null,
  "next_commit_name": null,
  "next_commit_assignee": null,
  "status": "active",
  "open_issues": [],
  "replan_history": []
}
EOF

# Commit protocol (minimal)
cat > commit-protocol.md << 'EOF'
# Commit Protocol

| # | Name | Owner | Status | Date |
|---|------|-------|--------|------|
EOF

# Token records
cat > TOKEN_RECORDS.md << 'EOF'
# Token Records

| Commit | Agent | Tokens | Date |
|--------|-------|--------|------|
EOF

# Commit specs directory
mkdir -p commit-specs
```

Copy the spec template:

```bash
cp <source>/manifesto/commit-specs/TEMPLATE.md commit-specs/
```

### Step 5 — Configure Agent Domains

Edit `hooks/agent-config.json` to match your project's file structure:

```json
{
  "agents": {
    "claude": {
      "domains": [
        "CLAUDE.md",
        ".claude/commands/",
        ".claude/persona-profiles.json",
        "commit-specs/",
        "hooks/",
        "docs/"
      ]
    },
    "your-backend-agent": {
      "domains": ["backend/", "src/api/"],
      "email": "agent@example.com"
    }
  }
}
```

### Step 6 — Adapt Personas

Edit `.claude/persona-profiles.json`:

1. **Update domain keywords** in the answer personas to match your stack
   (the current keywords reference FastAPI, SQLAlchemy, React, etc.)
2. **Update the interviewer challenge categories** if your project has
   different architectural concerns
3. **Update the contextual question templates** to reference your project's
   structure
4. **Add project-specific translation examples** to the founder persona
   (e.g., your domain's jargon → plain English mappings)

### Step 7 — Run the Codebase Scan

```bash
python hooks/forge_scan.py --path . --out .forge/
```

This creates `.forge/report.json` with your project's file graph. The
`/ask` question bank and `/forge` target-file identification both use
this data.

### Step 8 — Verify the Installation

```bash
# Test /ask
/ask what can this project do?
/ask eng questions

# Test /forge (dry run — look at the output, don't commit yet)
/forge add a health check endpoint

# Verify scan data
python -c "import json; r=json.load(open('.forge/report.json')); print(f'Files: {r[\"file_count\"]}, Categories: {list(r[\"category_summary\"].keys())}')"
```

### What to Customize

| Component | Why customize | How |
|-----------|--------------|-----|
| Stack profile | Different tech stack, frameworks, patterns | Edit `.claude/stack-profile.json` — this is the first thing to customize for a new project |
| Persona prompts | Stack-specific jargon, translation examples | Edit `persona-profiles.json` prompt arrays |
| Domain keywords | Different tech stack | Edit `ask.md` Phase 1 domain keywords |
| Agent config | Different team/domain structure | Edit `hooks/agent-config.json` |
| Forge scan rules | Different directory layout | Edit `hooks/forge_scan.py` category rules |
| Spec template | Different project conventions | Edit `commit-specs/TEMPLATE.md` |
| Interviewer wildcards | Domain-specific general knowledge | Edit interviewer persona prompts |

### What Works Out of the Box

- Persona selection (flag + memory + default)
- Question bank (evergreen + contextual generation)
- 3-tier pipeline (Quick/Standard/Deep)
- Interview mode (sessions, scoring, difficulty scaling)
- Forge phases (intent → scan → design → decompose → generate → validate)
- Next-step lifecycle (preflight → implement → verify → commit)
- Auto mode loop
- All presentation frames

---

## Design Decisions

The architectural decisions behind this system are recorded in
`DECISIONS.md` under **D55** (persona system + tiered pipeline). Key
highlights:

- **Personas over flags**: bundling language rules into selectable
  identities is simpler than composing `--no-code --plain-english` flags
- **3 tiers over 10 routes**: 55% prompt reduction, majority of questions
  are Quick or Standard (~95% of usage)
- **Interviewer in the same system**: reuses persona selection, question
  bank, and pipeline infrastructure without new commands
- **Forge is autonomous**: only asks the user for genuine architectural
  decisions, auto-resolves everything mechanical
- **Next-step is safe by default**: normal mode requires approval at every
  step, auto mode only proceeds on clean preflights
- **Ask generates forge prompts, not just answers**: the question bank
  and deep exploration sessions produce actionable `/forge` prompts
  alongside questions — closing the gap between "I understand the problem"
  and "I'm building the fix" without requiring the user to manually
  translate insights into tasks
- **The flow is composable**: each command works independently, but
  together they form a natural pipeline from understanding to execution
