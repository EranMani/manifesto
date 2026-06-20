# Development Flow — Ask, Forge, Execute

This document describes the complete development workflow powered by three
commands: `/ask`, `/forge`, and `/next-step`. Together they form a pipeline
that goes from "I have a question" to "the code is committed."

## Table of Contents

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
│   │          │          │          │          │          │     │
│   │ Persona  │          │ 6 phases │          │ Preflight│     │
│   │ Tiers    │          │ Scan     │          │ Implement│     │
│   │ Q&A      │          │ Agents   │          │ Verify   │     │
│   │ Interview│          │ Specs    │          │ Commit   │     │
│   └──────────┘          └──────────┘          └──────────┘     │
│                                                                 │
│   Read-only              Creates specs          Creates code    │
│   No side effects        Updates protocol       Updates state   │
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
- After 5+ questions in the same domain, suggests running `/forge`

**Key capability**: the question bank (`/ask pm questions`) generates
contextual questions from the actual codebase state — hub files, open
issues, recent changes. This gives new users an entry point without
needing to know what to ask.

**Output**: understanding. No files are created or modified.

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

The handoff from understanding to planning happens in two ways:

**Explicit**: the user runs `/forge` with a task based on what they learned:
```bash
# After learning that shipments can't be edited:
/forge add update endpoint for shipments
```

**Suggested**: after 5+ questions in the same domain, `/ask` suggests:
```
You're going deep on shipments. Want me to run /forge to turn these
insights into a commit spec?
```

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

### 1. Understand the current state

```bash
/ask pm what's the state of shipments?
```

Output reveals: CRUD exists but no pagination, no filtering, no update
endpoint. The PM persona presents this as a feature gap analysis.

### 2. Decide what to build

```bash
/ask eng how does the shipments endpoint handle large datasets?
```

Output reveals: `list_shipments()` returns `select(Shipment)` with no
limit — every row, every time. With growing data, this becomes a
performance problem.

### 3. Turn insight into a plan

```bash
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
copy-pasteable command to start the next focused session.

```
Recommended next session:
  Focus on migration safety and test isolation.
  Run: /ask ie migration safety and test isolation
```

This creates a continuous improvement loop separate from the development
flow — building architectural thinking, product instincts, and strategic
reasoning using the real codebase as the training ground.

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
└── development-flow.md           ← This file

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
                    │ .forge/report    │
                    │ project-state    │
                    └────────┬─────────┘
                             │ (insight)
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
- **The flow is composable**: each command works independently, but
  together they form a natural pipeline from understanding to execution
