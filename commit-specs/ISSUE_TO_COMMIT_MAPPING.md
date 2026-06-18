# Issue-to-Commit Mapping — Process Reference

> A reusable method for turning user-reported product issues into a validated commit
> sequence. Derived from the C68-C71 planning session (2026-06-18) and the C63-C67
> session (2026-06-17). Intended as a future feature specification for automating
> this workflow.

## The Problem This Solves

When a user reports multiple issues from hands-on product testing, the gap between
"these things are broken" and "here are the commits that fix them" requires:

1. Accurate root-cause analysis (not guessing from symptoms).
2. Agent-informed design discussion (not unilateral decisions).
3. Correct decomposition that respects ownership, budget, and dependency constraints.
4. Validated specs that pass `validate_commit_spec.py` before any implementation begins.

Getting any of these wrong wastes tokens — either by building the wrong fix, delegating
to the wrong agent, or failing validation and rewriting specs.

## Step-by-Step Process

### Step 1: Trace each issue to its root cause

Before invoking any agents, read the relevant source code and trace the exact execution
path for each reported symptom. The goal is to distinguish:

- **Misclassification bugs** — the input is routed to the wrong handler.
- **Unhandled exceptions** — the right handler runs but crashes.
- **Missing wiring** — a parameter or dependency is not passed.
- **Rendering/display bugs** — the backend is correct but the frontend doesn't format it.
- **Design gaps** — no code path exists for this use case.

**Worked example (C68-C71 session, 2026-06-18):**

Five reported issues traced to four distinct root causes:

| Reported symptom | Traced root cause | Category |
|---|---|---|
| "What are the employee leave rules?" → shipment error | `_POLICY_TERMS` missing "rules", "leave", "employee" — defaults to logistics | Misclassification |
| "Summarize vendor performance this month" → shipment error | "performance" not in any term list — defaults to logistics | Misclassification |
| "What does return policy say?" → HTTP 500 | `EmptyQueryError` not caught in policy handler; route handler only catches `LLMError` | Unhandled exception |
| "Summarize shipping guidelines" → HTTP 500 | Same unhandled exception path (correctly classified as policy) | Unhandled exception |
| "Which shipments are delayed?" → raw text | `llm` not passed to browse handler (missing wiring); frontend renders plain text (rendering bug) | Missing wiring + rendering |
| Evidence graph disorganized | Layout algorithm doesn't group by entity vs. event | Design gap |

**Key insight:** Two symptoms that look identical ("500 error") can have different root
causes (misclassification vs. unhandled exception). And one symptom ("raw text") can
have two contributing causes in different layers (backend missing wiring + frontend
missing formatting). Tracing before discussing prevents agents from solving the wrong
problem.

### Step 2: Invoke agents for design input — not implementation

Spawn specialist agents for **design discussion only** when:

- A product decision needs to be made (approach A vs. B).
- Domain expertise would improve the solution quality.
- The user explicitly requests agent involvement.

**Which agents to invoke:**

| Agent | When to invoke | What to ask |
|---|---|---|
| Mira (product) | User-facing behavior decisions, UX trade-offs | "Which approach gives users a better experience?" |
| Aria (frontend) | Frontend architecture, component design, layout algorithms | "How would you organize this UI? What's your layout proposal?" |
| Nova (AI/ML) | Intent classification, RAG pipeline, LLM prompt design | "How should the classifier handle this new category?" |
| Rex (backend) | API design, data model, service layer architecture | "What's the right service boundary for this fix?" |
| Sage (security) | Auth, input validation, error exposure | "Does this error message leak internal details?" |

**Rules for agent design discussions:**

1. State explicitly that this is a design discussion, not implementation.
2. Provide enough context that the agent can reason without scanning the repo.
3. Ask for recommendations, not code.
4. Cap response length (e.g., "under 400 words") to avoid token waste.
5. Accept that some agents may be blocked by circuit breakers — synthesize their
   perspective from the code you've already read when that happens.

**Worked example:**

- Mira was invoked for product decisions on badge formatting (markdown vs. action
  buttons), graph organization (entity vs. timeline split), and error messaging
  (honest scope vs. false negatives).
- Aria was blocked by `tool_cap_start.py` circuit breaker (prepared agent mismatch).
  Frontend design was synthesized from direct code analysis instead.
- A backend investigation agent (Explore type) was spawned to trace the 500 error
  chain across route handler → service → RAG pipeline → embedding service.

### Step 3: Map issues to commits

Group root causes into commits following these rules:

**Grouping criteria:**

1. **Same owner, same file** — group into one commit.
2. **Same owner, different files but same concern** — group if within the 4-file limit.
3. **Different owners** — must be separate commits (file ownership enforcement).
4. **Backend before frontend** — if the frontend depends on backend output format
   changes, the backend commit comes first.
5. **Classification before handling** — fix routing before fixing handlers, so tests
   can verify the full path.

**Splitting criteria:**

1. **Cross-domain file ownership** — never put Rex's files in Aria's commit.
2. **Budget limits** — max 4 changed files, max 350 diff lines, max 2 primary files.
3. **Dependency ordering** — if commit B needs commit A's output, they can't be parallel.
4. **Testability** — each commit should be independently verifiable.

**Worked example:**

Initial mapping had C70 (Aria) modifying `backend/app/services/rag_logistics.py` —
a Rex-domain file. `validate_commit_spec.py` caught this:

```
file_ownership: aria does not own backend/app/services/rag_logistics.py
```

Fix: moved the backend browse fallback formatting from C70 into C69 (Rex's commit).
C70 became frontend-only.

**Dependency chain:**

```
C68 (Nova: fix classification) → C69 (Rex: fix error handling + browse formatting)
  → C70 (Aria: markdown rendering) → C71 (Aria: graph timeline layout)
```

C68 and C69 are sequential because C69's error handling tests need C68's classification
fixes to verify the full path. C70 depends on C69 because the frontend needs the
backend to produce markdown-formatted output. C71 depends on C70 because the graph
labels may contain markdown.

### Step 4: Draft specs and validate

For each commit, write a spec following `commit-specs/TEMPLATE.md` with all required
sections:

**Required sections (from validator):**

- Primary Behavior (one sentence)
- Semantic Fit Review (atomic outcome, failure boundary, budget rationale)
- Execution Budget (yaml block with locked limits)
- Context (primary_files, initial_context, forbidden paths)
- Files To Modify Or Add (table with file, type, purpose)
- Contract (detailed change description per file)
- Environment Prerequisites
- Developer Test Checkpoint (milestone format: `**Next milestone:** CNN description`)
- Verification Command
- Focused Tests
- Done When
- Not In This Commit
- Return Contract

**Common validation failures and fixes:**

| Violation | Cause | Fix |
|---|---|---|
| `protocol_entry` | Commit not in `commit-protocol.md` | Add row to Commit Index table |
| `project_state` | `project-state.json` stale | Update `next_commit`, `next_commit_name`, `next_commit_assignee` |
| `file_ownership` | Wrong agent owns a file | Move file to correct agent's commit |
| `environment_prerequisites` | Section missing | Add `## Environment Prerequisites` |
| `developer_test_checkpoint` | Wrong format | Use `**Next milestone:** CNN description` for non-milestone commits |
| `dependency_missing` | Dependency commit not in protocol | Add dependency commit to protocol first |
| `max_changed_files` | Too many files (>4) | Split into additional commit or merge concerns |

**Validation sequence:**

1. Write all specs.
2. Update `project-state.json` (next_commit, tldr).
3. Add rows to `commit-protocol.md` (Commit Index + Phase result table).
4. Run `python hooks/validate_commit_spec.py --commit NN --json` for each.
5. Fix violations.
6. Run `python hooks/validate_commit_spec.py --all-pending --json` for the full graph.
7. All must return `"status": "valid"` with zero violations.

### Step 5: Present for approval

Show the user:

1. **Issue-to-commit mapping table** — which reported issue is fixed by which commit.
2. **Dependency chain** — what order they execute in and why.
3. **Agent input summary** — what the agents recommended and what was adopted.
4. **Execution decisions** — which commits are Claude-direct vs. delegated, with
   justification per CLAUDE.md criteria.

## Anti-Patterns

### Don't map symptoms 1:1 to commits
Two symptoms can share a root cause (one fix). One symptom can span two layers (two
commits). Always trace before mapping.

### Don't invoke agents for diagnosis
Agents are expensive. Use direct code reads and grep to trace root causes. Invoke
agents for design decisions, not for finding bugs.

### Don't let design discussion become implementation
Agent design responses should be recommendations, not code. The spec is the contract;
the agent implements from the spec, not from a chat discussion.

### Don't ignore file ownership
This is the most common spec validation failure. Check `AGENTS.md` or
`hooks/agent-config.json` domain boundaries before assigning files to commits.

### Don't skip the full-graph validation
Individual specs can pass while the dependency graph fails (e.g., a dependency commit
missing from `commit-protocol.md`). Always run `--all-pending` as the final check.

## Session Records

| Date | Issues | Commits | Document |
|------|--------|---------|----------|
| 2026-06-17 | 2 (browse queries fail, graph unreadable) | C63-C67 | `PHASE-3-PLANNING-SESSION.md` |
| 2026-06-18 | 5 (badges raw text, graph org, 500 errors, misclassification) | C68-C71 | This document + session below |

## C68-C71 Planning Session Record — 2026-06-18

### Trigger

Eran tested five assistant behaviors after C67 and reported:

1. Clicking "Which shipments are delayed?" badge shows unreadable raw text.
2. Evidence graph still not organized (entities mixed with events, no timeline).
3. "What does return policy say?" badge returns HTTP 500.
4. "Summarize vendor performance this month" and "What are the employee leave rules?"
   return "I couldn't find a shipment matching that query."
5. "Summarize the shipping guidelines" badge returns HTTP 500.

### Root cause tracing

Claude traced all five issues before invoking agents:

**500 errors (issues 3, 5):** Intent correctly classified as `policy` (terms
"return"/"policy"/"guidelines" found). The 500 originates in the embedding service
call chain: `generate_grounded_policy_answer` → `RAGPolicy.retrieve_evidence` →
`embed_query` → `EmbeddingService.embed_query()`. The route handler
(`api/v1/assistant.py:161`) only catches `LLMError`. `EmptyQueryError`
(`rag_policy.py:34`) is a plain `Exception` subclass, and any connection error from the
embedding provider also propagates unhandled.

**Wrong error message (issue 4):** `classify_intent()` checks `_POLICY_TERMS` (18
terms), `_BROWSE_TERMS` (10 terms), then defaults to `logistics` with confidence 0.5.
"Rules", "leave", "employee", "performance" are not in any term list. The default
logistics path calls `generate_grounded_logistics_answer` with an empty tracking code →
`ShipmentNotFoundError` → generic shipment message.

**Raw text (issue 1):** Two causes: (a) `assistant.py:60-62` calls
`generate_browse_logistics_answer` without passing `llm=llm`, so it skips LLM grounding
and uses only `_deterministic_browse_fallback` (plain text); (b) `Assistant.tsx:131`
renders all messages with `whitespace-pre-wrap` — no markdown rendering.

**Graph organization (issue 2):** `EvidenceGraph.tsx:67-112` uses column-based layout.
Events and products share column 4. No chronological sorting, no progression arrows.

### Agent invocations

| Agent | Purpose | Outcome |
|---|---|---|
| Explore (backend) | Trace 500 error chain | Completed: identified 4 bugs with file:line references |
| Explore (frontend) | Trace badge/graph behavior | Blocked by circuit breaker |
| Aria (frontend design) | Badge formatting + graph layout recommendations | Blocked by circuit breaker (prepared agent mismatch) |
| Mira (product review) | UX decisions on 3 issues | Completed: recommended hybrid badge approach, entity/timeline split, honest scope messaging |

When agents were blocked, Claude synthesized the missing perspective from code already
read.

### Mira's product recommendations (adopted)

1. **Badge responses:** Hybrid approach — structured table views for browse results,
   markdown for narrative answers. Tables with summary row + expandable detail.
2. **Graph organization:** Split into "Shipment Contents" (entity hierarchy) and
   "Event Timeline" (vertical chronological stack, current event highlighted).
3. **Error messages:** Be transparent about scope limits. Replace false "I couldn't find
   a shipment" with "I can answer logistics and policy questions. For [topic],
   you'll need [alternative]."

### Commit decomposition

| Commit | Owner | Root cause addressed | Why separate |
|---|---|---|---|
| C68 | Nova | Policy term misclassification | Intent vocabulary is Nova's RAG domain. Must land before C69 so error handling tests can verify the full corrected path. |
| C69 | Rex | Unhandled exceptions + missing LLM + browse formatting | All backend service/route fixes. Includes browse markdown formatting (moved from C70 to respect Aria's file ownership boundary). |
| C70 | Aria | Frontend plain-text rendering | Frontend-only: add `react-markdown`, render assistant messages as markdown. Depends on C69 producing markdown output. |
| C71 | Aria | Graph entity/event layout | Frontend-only: rewrite layout algorithm for two-group design. Independent of C70's concern but depends on it for timeline rendering. |

### Validation failures and fixes

1. **Missing protocol entries** — added C68-C71 rows to `commit-protocol.md` Commit
   Index and Phase 3 result table.
2. **Stale `project-state.json`** — updated `next_commit: "68"`, tldr, assignee.
3. **File ownership violation on C70** — `validate_commit_spec.py` caught
   `aria does not own backend/app/services/rag_logistics.py`. Moved browse fallback
   formatting to C69 (Rex).
4. **Missing sections** — added `Environment Prerequisites` and `Developer Test
   Checkpoint` to C68, C69, C71.
5. **Wrong checkpoint format** — changed from `**Not a milestone.**` to
   `**Next milestone:** C71 description` to match validator expectations.

Final validation: all 4 specs valid, full pending graph valid, zero violations.

### Files created

| File | Purpose |
|------|---------|
| `commit-specs/commit-68.md` | Spec for policy term expansion |
| `commit-specs/commit-69.md` | Spec for error resilience + browse formatting |
| `commit-specs/commit-70.md` | Spec for frontend markdown rendering |
| `commit-specs/commit-71.md` | Spec for evidence graph timeline layout |
| `commit-specs/ISSUE_TO_COMMIT_MAPPING.md` | This document |

### Files modified

| File | Changes |
|------|---------|
| `commit-protocol.md` | Added 4 pending rows (C68-C71), Phase 3 result table entries |
| `project-state.json` | Updated next_commit=68, tldr, assignee=nova |

## Future Feature: Automated Issue-to-Commit Pipeline

This document describes a manual process that could be partially automated. The
following components are candidates for tooling:

### 1. Issue intake and root-cause tracing
- Input: natural-language issue descriptions from user testing.
- Output: structured root-cause records with file:line, category (misclassification /
  exception / wiring / rendering / design gap), and affected code paths.
- Automation potential: high for exception tracing (stack trace analysis), medium for
  misclassification (intent classifier vocabulary audit), low for design gaps.

### 2. Agent routing for design input
- Input: root-cause records + agent roster.
- Output: which agents to invoke, with pre-formatted discussion prompts.
- Automation potential: high — agent selection is deterministic based on file ownership
  and issue category. Prompt generation follows a template.

### 3. Commit grouping and dependency ordering
- Input: root-cause records + file ownership map + budget constraints.
- Output: commit groups with dependency edges.
- Automation potential: high — file ownership lookup is a dict, budget limits are
  constants, dependency ordering follows layer rules (classification → handling →
  backend formatting → frontend rendering).

### 4. Spec generation and validation
- Input: commit groups + agent design recommendations + spec template.
- Output: validated spec files + protocol/state updates.
- Automation potential: medium — spec body requires judgment (contract details, test
  descriptions), but boilerplate sections (budget, context, checkpoint) are mechanical.
  Validation is already automated.

### 5. Approval presentation
- Input: validated specs + issue-to-commit mapping.
- Output: formatted summary for user approval.
- Automation potential: high — pure formatting.

### Integration points
- `validate_commit_spec.py` already enforces structural constraints.
- `hooks/agent-config.json` already maps agents to file domains.
- `commit-protocol.md` already tracks the commit sequence.
- `project-state.json` already tracks the active pointer.

A future `hooks/issue_to_commit.py` could orchestrate steps 1-4, producing draft specs
that only need contract details and user approval. The manual process documented above
is the specification for that tool's behavior.
