# /forge — Task-to-Commit Protocol Generator

The `/forge` command takes a plain-English task description and autonomously
produces a validated commit protocol — complete with specs, dependency chains,
agent routing, and budget allocations. It bridges the gap between "I want X"
and "here are the exact commits that build X."

## Table of Contents

- [Quick Start](#quick-start)
- [What It Does](#what-it-does)
- [The 6 Phases](#the-6-phases)
  - [Phase 1 — Intent Analysis](#phase-1--intent-analysis)
  - [Phase 2 — Codebase Scan](#phase-2--codebase-scan)
  - [Phase 3 — Agent Design Input](#phase-3--agent-design-input)
  - [Phase 4 — Commit Decomposition](#phase-4--commit-decomposition)
  - [Phase 5 — Spec Generation](#phase-5--spec-generation)
  - [Phase 6 — Approval Presentation](#phase-6--approval-presentation)
- [What Gets Created](#what-gets-created)
- [Auto-Resolve vs. Ask User](#auto-resolve-vs-ask-user)
- [Decomposition Rules](#decomposition-rules)
- [Architecture](#architecture)
  - [Files](#files)
  - [Dependencies](#dependencies)
- [Error Recovery](#error-recovery)
- [Connection to /ask and /next-step](#connection-to-ask-and-next-step)
- [Testing](#testing)

---

## Quick Start

```bash
# Simple feature request
/forge add pagination to the shipments endpoint

# Bug fix
/forge fix the chat scroll regression when messages overflow

# Multi-domain feature
/forge add document search with keyword highlighting across backend and frontend

# From an /ask session insight
/forge turn the shipment update gap into a commit spec
```

---

## What It Does

```
Plain-English task description
        │
        ▼
┌───────────────────┐
│  /forge pipeline  │
│                   │
│  1. Intent        │ ← What kind of task? Which domains?
│  2. Scan          │ ← Which files? Which hubs? Which agents own them?
│  3. Design        │ ← Agent input on approach (design only, no implementation)
│  4. Decompose     │ ← Split into atomic commits with dependency ordering
│  5. Generate      │ ← Full specs with all 14 required sections
│  6. Present       │ ← Validation results + approval card
│                   │
└───────────────────┘
        │
        ▼
Ready for /next-step execution
```

The output is not code — it's a validated plan. Implementation happens
in `/next-step`.

---

## The 6 Phases

### Phase 1 — Intent Analysis

Reads the task description and determines:

- **Task type**: feature / fix / refactor
- **Affected domains**: backend, frontend, devops, ai
- **Keywords**: domain-specific terms (routes, components, services, etc.)
- **Scope estimate**: XS / S / M / L based on file and domain count

Also reads `project-state.json` for current position (last completed
commit, pending work, blockers) and `commit-protocol.md` for the next
available commit number.

If there's already pending work, warns before proceeding:

```
FORGE — Intent Analysis

Task: add pagination to the shipments endpoint
Type: feature
Domains: backend
Keywords: shipments, pagination, endpoint
Estimated scope: S
Next available commit: C80
```

### Phase 2 — Codebase Scan

Runs the deterministic codebase scanner:

```bash
python hooks/forge_scan.py --path . --out .forge/
```

Produces `.forge/report.json` with:
- File categories (backend, frontend, devops, ai, docs, config)
- Import/call graph with bidirectional edges
- Hub files (high-connectivity load-bearing code)
- Domain ownership map (file to agent)

Cross-references scan results with Phase 1 keywords to identify the
exact target files the task will touch.

### Phase 3 — Agent Design Input

Based on which domains the task touches, invokes the relevant agents
for **design input only** — not implementation:

- **Backend** (Rex) — API design, data model, service layer
- **Frontend** (Aria) — Component design, layout, state management
- **AI services** (Nova) — Pipeline design, prompt engineering, RAG
- **DevOps** (Adam) — Infrastructure, deployment, automation
- **Product** (Mira) — Product review, UX decisions

If there's a genuine architectural decision (two viable approaches with
different tradeoffs), presents it to the user:

```
FORGE — Decision Required

Rex recommends approach A: Add limit/offset parameters to the existing endpoint
Nova recommends approach B: Add a new paginated endpoint alongside the existing one

Trade-off: A is simpler but breaks existing clients. B is backward-compatible but duplicates code.
Which approach? [A/B/other]
```

If no decision is needed, proceeds automatically.

### Phase 4 — Commit Decomposition

Runs the commit planner:

```bash
python hooks/forge_planner.py --report .forge/report.json \
    --task "add pagination" --task-type feature \
    --files backend/app/api/v1/shipments.py,backend/app/schemas/shipment.py \
    --out .forge/plan.json
```

Splits the task into atomic commits following these rules:
- One observable behavior per commit
- No cross-domain-ownership commits
- Backend before frontend (dependency ordering)
- Same owner + same concern = one commit (if 4 files or fewer)
- Different owners = separate commits

```
FORGE — Commit Plan

| # | Name | Owner | Scope | Execution | Depends on |
|---|------|-------|-------|-----------|------------|
| C80 | add-shipment-pagination | Rex | S | Claude-direct | — |
| C81 | add-shipment-list-filters | Rex | S | Claude-direct | C80 |

Dependency chain: C80 → C81
```

### Phase 5 — Spec Generation

Generates full commit specs using `commit-specs/TEMPLATE.md`. Each spec
has all 14 required sections:

1. Header (commit number, name, owner, phase, dependencies, estimates)
2. Primary Behavior (one sentence)
3. Semantic Fit Review (atomicity, failure boundary, budget rationale)
4. Execution Budget (locked YAML block)
5. Context (primary files, initial context, forbidden paths)
6. Files To Modify Or Add (table)
7. Contract (inputs, outputs, defaults, failure behavior)
8. Environment Prerequisites
9. Verification Command
10. Focused Tests (happy path, boundary, regression)
11. Done When (checklist)
12. Developer Test Checkpoint
13. Not In This Commit (deferred behavior)
14. Return Contract

Writes specs to `commit-specs/commit-NN.md`, updates `commit-protocol.md`
and `project-state.json`, then validates:

```bash
python hooks/validate_commit_spec.py --commit NN --json
python hooks/validate_commit_spec.py --all-pending --json
```

All specs must pass with zero violations before proceeding.

### Phase 6 — Approval Presentation

Presents the complete output:

```
FORGE COMPLETE — add pagination to shipments

Commits Created: C80, C81
Dependency Chain: C80 → C81
Agent Input: Rex recommended limit/offset with cursor fallback
Validation: 2/2 valid, zero violations
Estimated Cost: ~30,000 tokens

Ready for /next-step execution.
```

---

## What Gets Created

| File | Content |
|------|---------|
| `commit-specs/commit-NN.md` | Full spec for each commit (14 sections) |
| `commit-protocol.md` | Updated with new rows (status: pending) |
| `project-state.json` | Updated next_commit, tldr, replan_history |
| `.forge/report.json` | Codebase scan data (reusable for 1 hour) |
| `.forge/plan.json` | Commit decomposition plan |

---

## Auto-Resolve vs. Ask User

**Auto-resolved** (no user input needed):
- File ownership assignment (from agent-config.json)
- Budget allocation (locked constants from template)
- Commit numbering (next available from protocol)
- Boilerplate sections (Environment, Return Contract)
- Dependency ordering (topological sort by layer)
- Scope estimation (file count + hub involvement)

**Asks user** (requires judgment):
- Architecture decisions: "new service or extend existing?"
- Scope tradeoffs: "3 commits (minimal) or 7 commits (thorough)?"
- Priority conflicts: agents disagree on approach
- Ambiguous intent: "did you mean X or Y?"
- Existing pending work: "C79 is pending — add after it?"

---

## Decomposition Rules

From `commit-specs/ISSUE_TO_COMMIT_MAPPING.md`:

- **Same owner + same file** → one commit
- **Same owner + different files, same concern** → one commit if 4 files or fewer
- **Different owners** → separate commits
- **Backend before frontend** (dependency ordering)
- **Classification before handling** (fix the routing before fixing the handler)
- **Each commit = one observable behavior** (atomic, independently testable)

---

## Architecture

### Files

| File | Purpose |
|------|---------|
| `.claude/commands/forge.md` | Command definition — 6-phase pipeline |
| `hooks/forge_scan.py` | Deterministic codebase scanner (no LLM calls) |
| `hooks/forge_planner.py` | Commit decomposition engine |
| `hooks/validate_commit_spec.py` | Spec validation (14 sections, ownership, budget) |
| `commit-specs/TEMPLATE.md` | Spec template with all 14 required sections |
| `commit-specs/ISSUE_TO_COMMIT_MAPPING.md` | Decomposition rules and worked examples |
| `.forge/report.json` | Scan output (file graph, hubs, ownership) |
| `.forge/plan.json` | Decomposition output (commit sequence) |

### Dependencies

- Requires `hooks/forge_scan.py` and `hooks/forge_planner.py` to be functional
- Reads `hooks/agent-config.json` for domain ownership mapping
- Reads `commit-protocol.md` for commit numbering
- Reads `project-state.json` for current project position

---

## Error Recovery

- **Scanner fails**: reports error, suggests manual run with `--json`
- **Agent blocked**: synthesizes perspective from code (documents which agents were unavailable)
- **Validation loop**: after 3 failed attempts, presents violations to user for guidance
- **Budget impossible**: if task needs >4 files per owner per commit even after splitting, recommends phased approach

---

## Connection to /ask and /next-step

`/forge` is the middle step in the development flow:

```
/ask    → understand the codebase, identify gaps and opportunities
/forge  → turn insights into a validated commit plan
/next-step → execute the plan one commit at a time
```

The `/ask` command's session behavior explicitly suggests `/forge` when
a user goes 5+ questions deep in the same domain: "Want me to run `/forge`
to turn these insights into a commit spec?"

After `/forge` completes, the output ends with "Ready for /next-step
execution" — the handoff is direct.

---

## Testing

### Test intent analysis

```bash
/forge add a health check endpoint
```

**Check:** task type is "feature", domain is "backend", scope is XS/S.

### Test codebase scan

**Check:** `.forge/report.json` is created/refreshed, target files are
identified from keywords, hub files are listed.

### Test spec generation

**Check:** spec files exist at `commit-specs/commit-NN.md`, all 14
sections are present, `commit-protocol.md` has new rows.

### Test validation

```bash
python hooks/validate_commit_spec.py --commit NN --json
```

**Check:** returns `"status": "valid"` with zero violations.

### Test multi-domain decomposition

```bash
/forge add document upload with progress indicator in the UI
```

**Check:** produces separate commits for backend (Rex) and frontend (Aria),
with backend ordered before frontend.
