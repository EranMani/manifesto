# /next-step — Commit Execution Engine

The `/next-step` command reads the next pending commit from the protocol,
runs a preflight check, and — after approval — executes the full commit
lifecycle: implementation, verification, finalization, and state advancement.
It's the engine that turns `/forge` plans into committed code.

## Table of Contents

- [Quick Start](#quick-start)
- [What It Does](#what-it-does)
- [Execution Modes](#execution-modes)
  - [Normal Mode](#normal-mode)
  - [Auto Mode](#auto-mode)
  - [Auto-Once Mode](#auto-once-mode)
- [The Preflight Card](#the-preflight-card)
- [Execution Routes](#execution-routes)
  - [Claude-Direct](#claude-direct)
  - [Delegated](#delegated)
- [The Commit Lifecycle](#the-commit-lifecycle)
- [Auto Mode Loop](#auto-mode-loop)
- [Notifications](#notifications)
- [Architecture](#architecture)
  - [Files](#files)
  - [Hooks Pipeline](#hooks-pipeline)
- [Flags Reference](#flags-reference)
- [Command Patterns](#command-patterns)
- [Error Recovery](#error-recovery)
- [Connection to /ask and /forge](#connection-to-ask-and-forge)
- [Testing](#testing)

---

## Quick Start

```bash
# Normal mode — show preflight card, wait for approval
/next-step

# Auto mode — auto-approve clean preflights, loop through all pending commits
/next-step --auto

# Auto-once — run exactly one commit with auto behavior, then stop
/next-step --auto --once
```

---

## What It Does

```
/next-step
    │
    ▼
┌─────────────────────┐
│ Read project-state   │ ← Find next pending commit
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Choose execution     │ ← Claude-direct (default) or delegated
│ route                │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Run preflight        │ ← Validate spec, dependencies, ownership
└──────────┬──────────┘
           │
           ├── BLOCKED ──────► Show card, wait for user
           │
           ├── READY (manual) ► Show card, wait for approval
           │
           └── READY (auto) ─► Auto-approve, proceed to implementation
                    │
                    ▼
           ┌───────────────┐
           │ Implement      │ ← Edit files per spec
           ├───────────────┤
           │ Verify         │ ← Run tests + logic inspection
           ├───────────────┤
           │ Finalize       │ ← Constraint check + commit prep
           ├───────────────┤
           │ Commit         │ ← Primary commit + chore(state) sweep
           └───────┬───────┘
                   │
                   ├── (auto) ──► Loop to next pending commit
                   └── (once) ──► Stop
```

---

## Execution Modes

### Normal Mode

```bash
/next-step
```

1. Shows the preflight card for the next pending commit
2. Waits for explicit user approval ("yes")
3. Implements, verifies, and presents results
4. Waits for explicit commit approval
5. Commits and advances state

Every step requires user confirmation. This is the safe default.

### Auto Mode

```bash
/next-step --auto
```

1. Shows the preflight card
2. If READY with zero violations → auto-approves and proceeds
3. Implements, verifies, commits automatically
4. Advances state
5. **Loops to the next pending commit** and repeats
6. Stops when: preflight is blocked, verification fails, no more
   pending commits, or user sends a message

### Auto-Once Mode

```bash
/next-step --auto --once
```

Same as auto mode but runs exactly **one commit** then stops. No loop.
Useful for running a single commit unattended.

---

## The Preflight Card

Every `/next-step` invocation starts with a compact preflight card:

### Claude-direct card

```
C80 PREFLIGHT: READY

Owner: Rex (Backend)
Executor: Claude (direct)
Goal: Add pagination parameters to the shipments list endpoint

Files:
- Edit: backend/app/api/v1/shipments.py
- Edit: backend/app/schemas/shipment.py
- Add: backend/tests/api/test_shipment_pagination.py

Warnings:
- None.
- Decision required: No

Proceed? [yes/no]
```

### Delegated card

```
C80 PREFLIGHT: READY (87/100)

Owner: Nova (AI)
Executor: Nova (delegated)
Goal: Add semantic search fallback to policy RAG pipeline

Files:
- Edit: backend/app/services/rag_policy.py
- Add: backend/tests/services/test_rag_fallback.py

Warnings:
- None.
- Delegation justification: RAG pipeline requires specialist grounding in retrieval patterns
- Decision required: No

Proceed? [yes/no]
```

### Blocked card

```
C80 PREFLIGHT: BLOCKED

Owner: Aria (Frontend)
Executor: Claude (direct)
Goal: Add shipment list page with filtering

Files:
- Add: frontend/src/pages/ShipmentList.tsx

Warnings:
- Dependency C79 is not yet completed
- Decision required: No
```

---

## Execution Routes

### Claude-Direct

The default route. Claude implements the commit directly.

**When to use**: workflow changes, mechanical wiring, narrow repairs,
known edits, straightforward tests, and any task Claude can implement
from the selected context.

**Authorization**: narrow and commit-specific. Claude can only edit files
listed in the spec's "Files To Modify Or Add" table. The pre-commit hook
enforces this — staging any unlisted file fails the commit.

### Delegated

Used when specialist expertise justifies the invocation cost.

**When to use**: genuine specialist uncertainty (RAG pipeline design,
complex frontend state management, infrastructure with failure modes
Claude can't verify from context alone).

**Not sufficient reasons to delegate**: the file is "owned" by an agent,
the domain matches an agent's expertise, or "it's Rex's code." Domain
ownership is for review, not automatic execution.

**The delegation flow**:
1. Preflight runs with `prepare_agent_delegation.py --preview`
2. After approval, reruns without `--preview` to activate tool-cap state
3. Agent receives a generated brief and implements
4. Claude reviews the diff, runs verification, and commits

---

## The Commit Lifecycle

After approval, every commit follows this lifecycle regardless of route:

```
1. Implementation
   └─ Edit only files in "Files To Modify Or Add"

2. Verification
   ├─ Run the spec's verification command (pytest, etc.)
   ├─ Logic inspection against the commit contract
   └─ If fails → repair (max 2 cycles, then ask user)

3. Constraint verification
   └─ python hooks/verify_constraints.py --commit NN --agent OWNER

4. Finalization
   └─ python hooks/finalize_commit.py --commit NN --agent OWNER ...

5. Commit
   ├─ Primary commit: type(scope): description + Commit #NN
   └─ Chore commit: advance project-state.json + commit-protocol.md
      + TOKEN_RECORDS.md entry

6. State advancement
   ├─ project-state.json: last_completed → N, next_commit → N+1 or null
   ├─ commit-protocol.md: mark row as done
   └─ TOKEN_RECORDS.md: add row (never skip — no gaps allowed)
```

---

## Auto Mode Loop

In auto mode, the lifecycle repeats automatically:

```
┌──► Read project-state.json for next commit
│         │
│         ▼
│    Run preflight
│         │
│    ┌────┴────┐
│    │ READY?  │
│    └────┬────┘
│     yes │         no
│         │    ┌────────────┐
│         │    │ STOP: show │
│         │    │ card, wait │
│         │    └────────────┘
│         ▼
│    Implement → Verify → Finalize → Commit
│         │
│    ┌────┴────┐
│    │ --once? │
│    └────┬────┘
│     no  │     yes
│         │    ┌────────────┐
└─────────┘    │ STOP       │
               └────────────┘
```

**Stop conditions:**
- Preflight returns BLOCKED or has warnings
- Verification fails after 2 repair cycles
- `next_commit` is null (no more pending commits)
- User sends a message (interrupts the loop)
- `--once` flag is set (stop after this commit)

**Between commits**: shows a one-line status:

```
✓ C80 committed. Starting C81...
```

With `--once`:

```
✓ C80 committed. --once flag set, stopping. Next: C81.
```

---

## Notifications

Auto mode sends email notifications via `hooks/notify_agent_done.py`:

- **On success**: queued after both primary and chore commits succeed.
  Includes what completed, which checks passed, what's next.
- **On block**: queued when auto mode stops because approval or a
  decision is required. Includes what failed, why automatic continuation
  is unsafe, and a recommended resolution.
- **Not sent for**: successful `--once` stops, normal completion with
  no more pending commits, or user message interrupts.

---

## Architecture

### Files

| File | Purpose |
|------|---------|
| `.claude/commands/next-step.md` | Command definition — preflight, execution, auto mode |
| `hooks/preflight_commit.py` | Readiness check (spec, dependencies, ownership) |
| `hooks/prepare_agent_delegation.py` | Delegation package builder |
| `hooks/direct_execution_lifecycle.py` | Claude-direct context preparation |
| `hooks/verify_constraints.py` | Post-implementation constraint check |
| `hooks/finalize_commit.py` | Pre-commit finalization (markers, notifications) |
| `hooks/pre_commit_check.py` | Git pre-commit hook (domain boundary enforcement) |
| `hooks/context_telemetry.py` | Execution telemetry tracking |
| `hooks/notify_agent_done.py` | Email notification system |
| `project-state.json` | Current position, pending commits, blockers |
| `commit-protocol.md` | Commit index with status tracking |
| `TOKEN_RECORDS.md` | Per-commit token usage records |

### Hooks Pipeline

The hooks execute in this order during a commit:

```
preflight_commit.py          ← Can this commit proceed?
  │
direct_execution_lifecycle.py ← Prepare context (Claude-direct)
  │  OR
prepare_agent_delegation.py   ← Build delegation package
  │
  ▼
[Implementation happens here]
  │
  ▼
verify_constraints.py         ← Constraint check
  │
finalize_commit.py            ← Prepare commit artifacts
  │
pre_commit_check.py           ← Git hook: domain boundary enforcement
  │
[Commit happens]
  │
notify_agent_done.py          ← Email notification (auto mode)
```

---

## Flags Reference

| Flag | Effect |
|------|--------|
| (none) | Normal mode: show card, wait for approval at each step |
| `--auto` | Auto-approve READY preflights, auto-commit on verification pass, loop |
| `--auto --once` | Same as --auto but run exactly one commit, then stop |

---

## Command Patterns

### Tests (always in Docker)

```bash
docker compose run --rm backend uv run pytest <test-path> -x -q --tb=short
```

### Finalize (all arguments required)

```bash
python hooks/finalize_commit.py --commit NN --agent OWNER \
  --execution claude-direct --notify-what "SUMMARY" --notify-why "REASON"
```

### Primary commit

```bash
CLAUDE_COMMIT=1 git commit -m "$(cat <<'EOF'
type(scope): description

Commit #NN
Execution: Claude-direct

Co-Authored-By: Claude <claude@anthropic.com>
EOF
)"
```

### Chore state commit

```bash
CLAUDE_COMMIT=1 git commit -m "$(cat <<'EOF'
chore(state): advance state after CNN and update token records

Co-Authored-By: Claude <claude@anthropic.com>
EOF
)"
```

---

## Error Recovery

- **Preflight blocked**: shows the card with violations. User resolves
  or the blocking dependency completes first.
- **Verification fails**: repairs up to 2 cycles. After 2 failures,
  stops and asks the user for guidance.
- **Agent blocked**: falls back to Claude-direct with a note.
- **Budget exceeded**: stops with `SPLIT_REQUIRED` — completed work,
  remaining work, and proposed split.
- **Pre-commit hook fails**: domain boundary violation. Fix the staged
  files to match the spec's file list.

---

## Connection to /ask and /forge

`/next-step` is the final step in the development flow:

```
/ask        → understand the codebase
/forge      → turn insights into a validated commit plan
/next-step  → execute the plan, one commit at a time
```

`/ask` generates forge-ready prompts from codebase gaps (in the question
bank's "Build next" section, after deep exploration, and in interview
scorecards). `/forge` turns those prompts into validated commit specs.
`/next-step` reads the specs and executes. The full pipeline:

```
/ask pm q → "Build next" → /forge {prompt} → /next-step --auto
```

The handoff from `/forge` is automatic — it ends with "Ready for
/next-step execution" and `/next-step` reads `project-state.json` to
find what's next.

---

## Testing

### Test normal mode

```bash
/next-step
```

**Check:** preflight card appears, waits for approval, does not start work.

### Test auto mode stops on block

Create a commit with an unmet dependency. Run `/next-step --auto`.
**Check:** card shows BLOCKED, does not auto-approve.

### Test auto-once

```bash
/next-step --auto --once
```

**Check:** runs one commit fully (preflight → implement → verify → commit →
state advance), then stops. Shows "stopping" message.

### Test state advancement

After a commit completes, verify:
- `project-state.json`: `last_completed_commit` advanced
- `commit-protocol.md`: row marked done
- `TOKEN_RECORDS.md`: new row added (no gaps)
- `git status`: clean (no uncommitted protocol files)
