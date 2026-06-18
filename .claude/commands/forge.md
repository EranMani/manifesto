# /forge — Autonomous Task-to-Commit-Protocol Generator

Parse `$ARGUMENTS` as a free-text task description. If empty, ask: "What task should
I forge into a commit protocol?"

This command autonomously produces a validated commit protocol with specs from a
plain-English task description. It runs through 6 phases, asking the user only for
genuine architectural decisions — everything mechanical is auto-resolved.

---

## Phase 1 — Intent Analysis

Read the task description and determine:

1. **Task type**: feature / fix / refactor
2. **Affected domains**: backend, frontend, devops, ai (can be multiple)
3. **Keywords**: extract domain-specific terms (API routes, components, services,
   models, migrations, Docker, hooks, LLM, RAG, etc.)
4. **Scope estimate**: how many files and domains are likely involved

Read `project-state.json` for:
- `last_completed_commit` — where we are in the sequence
- `next_commit` — whether there's already a pending commit
- `blockers` — anything that would prevent new work
- `open_handoffs` — relevant cross-domain context

Read `commit-protocol.md` to find the next available commit number and understand the
existing sequence.

If `next_commit` is not null, warn the user:
```
⚠ There is already a pending commit: C[N] `[name]`. Forging new commits will
add them after the current pending work. Continue? [yes/no]
```

Present the intent analysis:
```
FORGE — Intent Analysis

Task: [original text]
Type: [feature/fix/refactor]
Domains: [backend, frontend, ...]
Keywords: [extracted terms]
Estimated scope: [XS/S/M/L]
Next available commit: C[N]
```

---

## Phase 2 — Codebase Scan (Graph RAG)

Run the codebase scanner:
```
python hooks/forge_scan.py --path . --out .forge/
```

This produces `.forge/report.json` with:
- File categories (backend, frontend, devops, ai, docs, config, other)
- Import/call graph with bidirectional edges
- Hub files (high in-degree or out-degree — load-bearing code)
- Domain ownership map (file → agent from agent-config.json)

Read `.forge/report.json` and cross-reference with the Phase 1 keywords to identify
the **target files** — the specific files the task will touch. Use these signals:

1. **Direct keyword match**: task mentions "assistant" → `backend/app/services/assistant.py`
2. **Hub proximity**: if a target file imports a hub, the hub may need changes too
3. **Domain boundaries**: use `domain_ownership` to verify which agent owns each file
4. **Call-tree tracing**: follow imports to find upstream/downstream dependencies

Present the scan results:
```
FORGE — Codebase Scan

Files scanned: [N]
Categories: backend([N]), frontend([N]), ai([N]), devops([N])
Hubs identified: [top 3-5 by connectivity]

Target files for this task:
- [file] (owner: [agent], category: [cat])
- [file] (owner: [agent], category: [cat])
...

Domains involved: [list]
Agents needed: [list]
```

---

## Phase 3 — Agent Routing & Design Input

Based on the domains the task touches, invoke agents for **design input only** — not
implementation. Agent selection is deterministic:

| Domain touched | Agent | Purpose |
|---------------|-------|---------|
| backend/ | Rex | API design, data model, service layer |
| frontend/ | Aria | Component design, layout, state management |
| AI services | Nova | Pipeline design, prompt engineering, RAG |
| DevOps/hooks | Adam | Infrastructure, deployment, automation |
| User-facing behavior | Mira | Product review, UX decisions |

Rules:
- State explicitly: "This is a design discussion for /forge planning. Do not implement."
- Provide the task description and the target files from Phase 2.
- Ask for: recommended approach, file changes, risks, and testing strategy.
- Cap responses: "Under 400 words."
- If an agent is blocked by the circuit breaker, synthesize their perspective from
  the code and scan report already available. State: "Note: [Agent] was unavailable;
  perspective synthesized from code analysis."

If the task involves a **genuine architectural decision** (two viable approaches with
different trade-offs), present it to the user:
```
FORGE — Decision Required

[Agent] recommends approach A: [description]
[Agent] recommends approach B: [description]

Trade-off: [what you gain/lose with each]
Which approach? [A/B/other]
```

If no decision is needed, proceed automatically.

---

## Phase 4 — Commit Decomposition

Run the commit planner with the target files from Phase 2:
```
python hooks/forge_planner.py --report .forge/report.json \
    --task "[task description]" \
    --task-type [feature/fix/refactor] \
    --files [comma-separated target files] \
    --out .forge/plan.json
```

Read `.forge/plan.json`. For each commit in the plan, apply these naming rules:
- Slug: `kebab-case`, max 6 words, descriptive of the primary behavior
- Pattern: `[verb]-[noun]-[qualifier]` (e.g., `add-rate-limit-middleware`)

Refine the plan using agent design input from Phase 3:
- Adjust file assignments based on agent recommendations
- Add or remove commits if agents identified missing or unnecessary changes
- Verify each commit has exactly one observable behavior (atomic)
- Verify no commit crosses domain ownership boundaries

Apply the decomposition rules from `commit-specs/ISSUE_TO_COMMIT_MAPPING.md`:
- Same owner + same file → one commit
- Same owner + different files, same concern → one commit if ≤ 4 files
- Different owners → separate commits
- Backend before frontend (dependency ordering)
- Classification before handling

Present the decomposition:
```
FORGE — Commit Plan

| # | Name | Owner | Scope | Execution | Depends on |
|---|------|-------|-------|-----------|------------|
| C[N] | [slug] | [agent] | [XS/S/M/L] | [direct/delegated] | — |
| C[N+1] | [slug] | [agent] | [XS/S/M/L] | [direct/delegated] | C[N] |

Dependency chain: C[N] → C[N+1] → ...
Agents consulted: [list with one-line summary of each recommendation]
Estimated total tokens: [N]
```

---

## Phase 5 — Spec Generation & Validation

For each commit in the plan, generate a full spec using the template at
`commit-specs/TEMPLATE.md`. Each spec must include all 14 required sections:

1. **Header** — commit number, name, owner, phase, depends_on, estimated diff lines,
   primary behavior count, developer test milestone
2. **Primary Behavior** — one sentence describing the observable behavior
3. **Semantic Fit Review** — atomic outcome, failure boundary, budget rationale
4. **Execution Budget** — the locked YAML block (copy from TEMPLATE.md)
5. **Context** — primary_files, initial_context, forbidden paths
6. **Files To Modify Or Add** — table with file, type, purpose
7. **Contract** — exact inputs, outputs, defaults, failure behavior
8. **Environment Prerequisites** — runtime, services, fixtures
9. **Verification Command** — single focused pytest or equivalent
10. **Focused Tests** — happy path, boundary path, regression
11. **Done When** — checklist of completion criteria
12. **Developer Test Checkpoint** — milestone format
13. **Not In This Commit** — deferred behavior with owning commit
14. **Return Contract** — standard implementor summary format

Write each spec to `commit-specs/commit-[N].md`.

Update `commit-protocol.md`:
- Add rows to the Commit Index table for each new commit
- Mark status as `pending`

Update `project-state.json`:
- Set `next_commit` to the first new commit number (only if currently null)
- Update `tldr` to reflect the new planned work
- Add a `replan_history` entry with date, trigger (the task description),
  summary, agents consulted, and files updated

Validate every spec:
```
python hooks/validate_commit_spec.py --commit [N] --json
```

If validation fails:
- **File ownership violation**: move the file to the correct agent's commit
- **Missing section**: add the section with appropriate content
- **Budget exceeded**: split the commit
- **Protocol entry missing**: add the row to commit-protocol.md

After fixing, re-validate. Then run the full graph check:
```
python hooks/validate_commit_spec.py --all-pending --json
```

All specs must return `"status": "valid"` with zero violations before proceeding.

---

## Phase 6 — Approval Presentation

Present the complete forge output:

```
FORGE COMPLETE — [task summary]

## Commits Created

| # | Name | Owner | Execution | Files | Scope |
|---|------|-------|-----------|-------|-------|
| C[N] | [slug] | [agent] | [mode] | [count] | [XS/S/M/L] |

## Dependency Chain
C[N] → C[N+1] → ...

## Agent Input Summary
- [Agent]: [one-line summary of recommendation and what was adopted]

## Execution Decisions
- C[N]: [Claude-direct/delegated] — [justification]

## Validation
- Individual specs: [N]/[N] valid
- Full pending graph: valid
- Zero violations

## Estimated Cost
- Total tokens: ~[N]
- Delegated commits: [N] × 45,000 implementor tokens
- Claude-direct commits: [N] × ~15,000 orchestrator tokens

## Files Written
- commit-specs/commit-[N].md ... commit-specs/commit-[M].md
- commit-protocol.md (updated)
- project-state.json (updated)

Ready for /next-step execution.
```

## Auto-resolve vs. Ask User

**Auto-resolve** (no user intervention):
- File ownership assignment (deterministic from agent-config.json)
- Budget allocation (locked constants)
- Commit numbering (next available from protocol)
- Boilerplate sections (Environment Prerequisites, Return Contract)
- Dependency ordering (topological sort by layer)
- Scope estimation (file count + hub involvement)

**Ask user** (requires judgment):
- Architecture decisions: "Should we add a new service or extend the existing one?"
- Scope trade-offs: "This could be 3 or 7 commits — minimal or thorough?"
- Priority conflicts: "Two approaches exist; agents disagree on which"
- Ambiguous intent: "Did you mean X or Y?"
- Existing pending work: "C[N] is already pending — add after it?"

---

## Error Recovery

If any phase fails:
- **Scanner fails**: report the error and suggest running manually with `--json`
- **Agent blocked**: synthesize from code (document which agents were unavailable)
- **Validation loop**: after 3 failed validation attempts, present the violations
  to the user and ask for guidance
- **Budget impossible**: if the task requires >4 files per owner per commit even
  after splitting, recommend a phased approach and ask the user to narrow scope
