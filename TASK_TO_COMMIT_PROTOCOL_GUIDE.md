# Task To Commit Protocol Guide

**Purpose:** Convert a user task or mission into a dependency-ordered commit protocol
made of bounded, valid commit specifications.

**Audience:** Human planners now; an automated planning system later.

**Authority:** This guide applies the rules in:

- `MULTI_AGENT_WORKFLOW_REDESIGN_ROADMAP.md`
- `commit-protocol.md`
- `commit-specs/TEMPLATE.md`
- `AGENTS.md`
- `hooks/validate_commit_spec.py`

If this guide conflicts with an enforced hook or an approved roadmap decision, the
enforced hook or approved decision wins.

---

## 1. Expected Input And Output

### Input

A user supplies a mission description. It may be broad, incomplete, or written without
technical boundaries.

Example:

> Add policy chat with streamed answers, saved conversations, and citations.

The planning process may also receive:

- Existing repository structure.
- Current commit number and project state.
- Agent roster and ownership boundaries.
- Existing architecture and contracts.
- Known defects, dependencies, and environment constraints.
- Required acceptance criteria.

### Output

The process produces:

1. A normalized mission contract.
2. A list of independently observable behaviors.
3. A domain and owner map.
4. A dependency graph.
5. A sequential commit protocol.
6. One valid commit specification per commit.
7. A validation and approval report.

The output is a plan. It does not authorize implementation.

---

## 2. Locked Commit Limits

Every normal implementation commit must fit:

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 350
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

These are hard ceilings, not targets.

A good plan should leave safety margin. Prefer:

- 1 primary behavior.
- 1-2 primary files.
- 2-3 changed files.
- 200-280 estimated changed lines.
- 3-5 initial context files.
- One focused test command.

Do not intentionally fill every limit. Estimation is uncertain.

---

## 3. Core Planning Rules

Every commit must have:

- One observable primary behavior.
- One owner.
- One domain whenever possible.
- One explicit dependency set.
- Exact files to modify or add.
- Focused tests that prove the behavior.
- One concrete verification command.
- Explicit environment prerequisites.
- Explicit exclusions in `Not In This Commit`.
- Acceptance criteria that can be checked without interpretation.

Every commit must be:

- Independently understandable.
- Independently testable.
- Safe to stop after.
- Small enough for one normal agent invocation.
- Useful without relying on uncommitted future work.

Commits use sequential integer IDs. Do not create ordinary planning IDs such as `C30a`,
`C30.1`, or temporary semantic suffixes.

---

## 4. The Decomposition Pipeline

### Step 1: Normalize The Mission

Rewrite the user request as a short contract:

```yaml
mission:
  goal: "What capability should exist?"
  users: ["Who receives the capability?"]
  observable_outcomes:
    - "What can a user or system observe?"
  constraints:
    - "Security, compatibility, performance, or workflow constraints"
  non_goals:
    - "What is explicitly excluded?"
  unknowns:
    - "Questions that affect architecture or scope"
```

Do not create commits while important product or architecture decisions remain unknown.
Resolve or explicitly defer those decisions first.

### Step 2: Inspect Existing Reality

Before decomposing, identify:

- Existing implementation files.
- Existing tests and fixtures.
- Existing APIs, schemas, models, and migrations.
- Current stubs or placeholders.
- Domain ownership from `AGENTS.md`.
- Completed commits that provide dependencies.
- Pending work that overlaps the mission.

The planner should use targeted repository inspection. It should not assume that the
mission starts from an empty project.

### Step 3: Extract Observable Behaviors

Break the mission into statements that can be proven externally.

Good behavior:

> A duplicate document upload returns HTTP 200 without creating another row.

Bad behavior:

> Improve document uploads.

Use this pattern:

> Given [starting condition], when [action occurs], then [observable result].

Do not combine behaviors with `and` unless they are inseparable parts of one atomic
contract.

### Step 4: Classify By Work Type

Assign each behavior to one primary work type:

| Type | Typical artifacts |
|---|---|
| Governance | Protocols, specs, agent instructions |
| Agent hooks | Enforcement, delegation, verification hooks |
| Context package | Context rules, graph selection, briefs |
| Telemetry | Invocation records, aggregation, reconciliation |
| Dashboard | Operator views and status presentation |
| Environment | Docker, runtime, test preflight |
| Database | Models, migrations, repository queries |
| Backend API | Routes, request/response schemas |
| Service logic | Business rules, ingestion, retrieval |
| Frontend transport | API clients, SSE parsing, cancellation |
| Frontend UI | Pages, components, interaction state |
| Quality | Integration tests, evaluation, security review |

This classification prevents unrelated work from being hidden inside one commit.

### Step 5: Assign The Owner

Use `AGENTS.md` as the ownership authority.

Rules:

- Assign one implementor per commit.
- Prefer files already owned by that agent.
- Split cross-domain work into separate commits with a contract boundary.
- Use a handoff when a later owner consumes an earlier contract.
- Reviewers do not implement.
- Claude orchestrates and governs; Claude does not absorb application work that exceeds
  an implementor's scope.

If no agent owns a required path, add or approve the ownership boundary before execution.

### Step 6: Build The Dependency Graph

Create behavior nodes before assigning commit numbers.

Use these dependency categories:

- **Contract dependency:** a consumer needs a stable API or data shape.
- **Data dependency:** a model or migration must exist first.
- **Verification dependency:** a test baseline or environment must exist first.
- **Workflow dependency:** enforcement must exist before risky work resumes.
- **UI dependency:** the frontend requires a stable backend contract.

Prefer vertical progress, but do not combine domains merely to create a complete feature
in one commit.

Example:

```text
database schema
  -> service persistence
  -> history API
  -> frontend history client
  -> sidebar UI
```

Parallel work is permitted only when:

- Dependencies are already frozen.
- File ownership does not overlap.
- Neither commit needs the other's uncommitted output.

### Step 7: Form Candidate Commits

Create one candidate commit for each behavior-owner pair.

Candidate format:

```yaml
candidate:
  name: focused-kebab-name
  behavior: "One observable result"
  owner: rex
  work_type: backend_api
  depends_on: ["candidate-id"]
  primary_files:
    - exact/path.py
  changed_files:
    - exact/path.py
    - exact/test_path.py
  estimated_diff_lines: 180
  verification_command: "pytest exact/test_path.py -q"
  exclusions:
    - "Related behavior owned by a later candidate"
```

Do not assign final commit numbers until the candidate graph is stable.

---

## 5. How To Decide When To Split

Split a candidate when any answer below is yes.

### Behavior Test

- Does the description contain two independently testable outcomes?
- Could one outcome pass while another fails?
- Could one outcome be released or reverted independently?

If yes, split by behavior.

### Ownership Test

- Does the candidate modify files owned by different implementors?
- Does it combine backend, frontend, database, or workflow implementation?

If yes, split at the contract boundary.

### File Test

- More than two primary implementation files?
- More than four total changed files?
- Vague files such as "related components" or wildcard paths?

If yes, narrow or split.

### Size Test

- More than 350 estimated changed lines?
- Does the estimate depend on generated code not explicitly declared?
- Is a primary file already large enough that discovery and modification are risky?

If yes, split and leave margin.

### Context Test

- More than six initial context files?
- More than 15,000 estimated context characters?
- Does understanding the task require broad directory exploration?

If yes, establish an earlier contract or discovery decision. Do not solve it by giving
the agent a larger package.

### Verification Test

- Does the candidate require several unrelated verification commands?
- Does it mix unit, database, browser, and infrastructure acceptance?
- Can no single focused command prove its primary behavior?

If yes, split by verification boundary.

### Risk Test

- Does it combine schema migration and broad application behavior?
- Does it combine transport parsing and full UI behavior?
- Does it combine retrieval, ranking, prompt construction, generation, and evaluation?
- Does it mix a defect repair with a new feature?

If yes, split by failure mode.

### Agent-Capacity Test

Ask:

> Can one prepared agent understand, implement, test, and report this work within one
> invocation, 18 tool calls, and 45,000 tokens without broad discovery?

If the answer is uncertain, split.

---

## 6. Recommended Splitting Patterns

### Contract Before Consumer

1. Define or implement the backend contract.
2. Implement the client against the frozen contract.
3. Add user-facing integration.

### Schema Before Behavior

1. Add the migration and model representation.
2. Add service persistence.
3. Add API exposure.
4. Add UI consumption.

### Data Pipeline

1. Candidate retrieval.
2. Ranking.
3. Context selection.
4. Generation transport.
5. Citation validation.
6. Evaluation.

### Streaming UI

1. Transport parser and typed events.
2. Page state and incremental rendering.
3. Cancellation and retry controls.
4. History loading.
5. Citation presentation.

### Telemetry

1. Immutable invocation storage.
2. Commit aggregation and contradiction detection.
3. Dashboard/operator presentation.

### Defect And Feature

1. Repair the existing contract with regression tests.
2. Establish the required test or environment baseline.
3. Build the new feature afterward.

---

## 7. Estimation Method

Estimates must be conservative and written before implementation.

### Changed Files

Count:

- Every implementation file.
- Every test file.
- Every schema, migration, configuration, or fixture changed.
- Generated files unless an exact exception is approved.

Do not count directories. Do not use wildcards.

### Diff Lines

Estimate additions plus deletions.

Suggested planning ranges:

| Work | Typical estimate |
|---|---:|
| Small contract correction with tests | 80-180 |
| Focused hook behavior with tests | 150-260 |
| Small route plus schema and tests | 180-300 |
| Focused service algorithm plus tests | 200-320 |
| One frontend client or component behavior | 180-300 |
| Migration plus model test | 180-300 |

If the estimate approaches 350, split before writing the spec.

### Context

Initial context normally includes:

1. The active commit spec.
2. The primary implementation file.
3. The focused test file.
4. One consumed contract.
5. One identity or supporting file when required.

Reserve the sixth slot for an essential dependency. Do not preload optional references.

---

## 8. Naming And Numbering

Commit names should describe the behavior, not the entire feature.

Good:

- `upload-duplicate-status`
- `invocation-record-storage`
- `policy-rank-fusion`
- `chat-sse-parser`

Bad:

- `finish-chat`
- `rag-system`
- `backend-updates`
- `misc-fixes`

After candidates validate:

1. Topologically sort the dependency graph.
2. Apply product priority.
3. Assign the next sequential integer IDs.
4. Update dependencies to final IDs.
5. Update protocol rows, filenames, headings, handoffs, and project state together.
6. Validate the full pending graph.

Completed commit IDs never change.

---

## 9. Building The Commit Protocol

The protocol is the concise execution index.

Each row needs:

| Field | Meaning |
|---|---|
| Number | Sequential commit ID |
| Name | Focused kebab-case behavior |
| Assignee | One owning agent |
| Status | Pending, active, blocked, or done |

The protocol should also include:

- Dependency order.
- Approved parallel groups.
- Phase boundaries.
- Product freezes or workflow prerequisites.
- Rules for approval and `SPLIT_REQUIRED`.

The protocol is not a substitute for commit specs. It tells the team what runs and in
what order.

---

## 10. Building Each Commit Specification

Create each file from `commit-specs/TEMPLATE.md`.

### Primary Behavior

State one externally observable outcome.

### Execution Budget

Copy the locked values. Never raise them to make a candidate pass.

### Context

List exact:

- Primary files.
- Initial context files.
- Forbidden paths.

### Files To Modify Or Add

List exact paths and purposes. Maximum four normal changed files.

### Contract

Define relevant:

- Inputs.
- Outputs.
- Defaults.
- Status codes.
- Event or schema shapes.
- Ordering.
- Error behavior.
- Security and ownership behavior.

### Environment Prerequisites

State what must work before the agent is invoked. Environment debugging should not
consume the implementation budget.

### Verification Command

Provide one runnable command that proves the primary behavior.

### Focused Tests

Include:

- Happy path.
- Boundary or rejection path.
- Regression assertion.

### Done When

Use objective checkboxes. Avoid phrases such as "works correctly" without a measurable
condition.

### Developer Test Checkpoint

Mark a commit as a developer test milestone only when it completes a coherent capability
that can be tested through an API, dashboard, service boundary, or visible application
workflow.

The milestone must define:

- What is ready now.
- Exact startup and test steps.
- The expected observable result.
- What remains intentionally incomplete.

Do not create milestones at arbitrary intervals such as every five commits. Several
micro-commits may combine into one useful checkpoint.

### Not In This Commit

Name excluded work and the later commit that owns it.

### Return Contract

Require the Human Summary, structured telemetry, and `SPLIT_REQUIRED` when completion is
not credible within budget.

---

## 11. Validation And Approval Loop

For every proposed spec:

1. Run `hooks/validate_commit_spec.py`.
2. Correct structural violations.
3. Reassess semantic size even when validation passes.
4. Confirm dependencies exist.
5. Confirm ownership boundaries.
6. Confirm the initial context fits.
7. Confirm one verification command can prove the behavior.
8. Present the protocol and specs to Eran.
9. Continue only after explicit approval.

A validator pass means the document satisfies machine-checkable structure. It does not
prove the task is semantically small enough. The planner remains responsible for
conservative decomposition.

---

## 12. Runtime Scope Failure

Planning reduces uncertainty but cannot eliminate it.

During implementation:

- Call 12 triggers a budget status report.
- By call 16, the agent decides whether completion by call 18 is credible.
- Call 19 is blocked.
- Expansion 3 is blocked.

If completion is not credible, the agent returns `SPLIT_REQUIRED`.

Claude then:

1. Stops execution.
2. Evaluates whether completed work is independently safe and atomic.
3. Drafts a new candidate for unfinished work.
4. Re-runs this decomposition process.
5. Assigns sequential numbers only after the revised graph is stable.
6. Presents the change to Eran.
7. Continues only after approval.

The budget is never waived. Claude does not finish oversized application work directly.

---

## 13. Machine-Oriented Planning Record

A future planning system should preserve an intermediate decomposition record before it
writes Markdown specs.

```json
{
  "mission": {
    "goal": "Add policy chat",
    "observable_outcomes": [],
    "constraints": [],
    "non_goals": [],
    "unknowns": []
  },
  "behaviors": [
    {
      "id": "B01",
      "statement": "Authenticated users receive typed SSE events",
      "work_type": "backend_api",
      "owner": "rex",
      "depends_on": ["B00"],
      "primary_files": ["backend/app/api/v1/chat.py"],
      "changed_files": [
        "backend/app/api/v1/chat.py",
        "backend/app/schemas/chat.py",
        "backend/tests/api/test_chat_policy.py"
      ],
      "estimated_diff_lines": 260,
      "verification_command": "pytest backend/tests/api/test_chat_policy.py -q",
      "not_in_commit": ["Persistence", "Frontend rendering"],
      "budget_assessment": {
        "status": "fits",
        "violations": [],
        "risk": "medium"
      }
    }
  ],
  "edges": [
    {
      "from": "B00",
      "to": "B01",
      "type": "contract_dependency"
    }
  ],
  "protocol": [
    {
      "commit": "C42",
      "behavior_id": "B01",
      "name": "policy-chat-sse-route",
      "owner": "rex",
      "status": "pending"
    }
  ],
  "approval": {
    "status": "awaiting_user",
    "approved_at": null
  }
}
```

This record allows a future system to:

- Explain why a split occurred.
- Recalculate numbering.
- Detect dependency and ownership conflicts.
- Generate protocol rows and commit specs.
- Compare planned scope with runtime `SPLIT_REQUIRED` reports.

---

## 14. Planning Statuses

Use explicit statuses:

| Status | Meaning |
|---|---|
| `needs_clarification` | A missing decision changes scope or architecture |
| `candidate` | Behavior identified but not budgeted |
| `split_required` | Candidate exceeds or risks exceeding limits |
| `fits` | Candidate passes structural and semantic sizing |
| `validated` | Generated spec passes the validator |
| `awaiting_user` | Protocol/specs require Eran's approval |
| `approved` | Planning is approved for execution |
| `blocked` | External dependency prevents safe execution |

Do not treat `validated` as `approved`.

---

## 15. Common Planning Failures

Reject these patterns:

- One commit named after an entire feature or epic.
- `fits_single_agent: true` without evidence.
- Raising budgets instead of splitting scope.
- Multiple domains under one owner.
- More than one verification surface.
- Tests deferred to a later commit.
- Migration, service, API, and UI combined.
- Research-only invocation followed by a second normal invocation.
- Vague paths such as `related files`.
- Hidden cleanup or refactoring inside feature work.
- A dashboard or telemetry view combined with its storage redesign.
- A status-code defect bundled into a larger feature.
- Numbering commits before dependencies and sizing are stable.
- Automatically accepting an AI-generated plan without user approval.

---

## 16. Final Planning Checklist

Before presenting a protocol:

- [ ] The mission has observable outcomes and explicit non-goals.
- [ ] Existing repository reality was inspected.
- [ ] Every behavior has one owner and one work type.
- [ ] Dependencies form a valid acyclic graph.
- [ ] Every candidate has one primary behavior.
- [ ] No candidate exceeds two primary files.
- [ ] No candidate exceeds four changed files.
- [ ] No candidate exceeds 350 estimated diff lines.
- [ ] Every candidate fits six context files and 15,000 characters.
- [ ] Every candidate has one focused verification command.
- [ ] Every candidate includes tests.
- [ ] Coherent technical and application test milestones are identified.
- [ ] Every milestone has exact manual steps and an expected result.
- [ ] No milestone is based only on elapsed commit count.
- [ ] Cross-domain work is separated by explicit contracts.
- [ ] Risky candidates were split with safety margin.
- [ ] Final IDs are sequential integers.
- [ ] Protocol rows, filenames, headings, and dependencies agree.
- [ ] Every spec passes `hooks/validate_commit_spec.py`.
- [ ] Human-readable reasons for each split are available.
- [ ] The plan is marked `awaiting_user` until explicitly approved.

---

## 17. Definition Of A Successful Decomposition

A mission is successfully decomposed when:

- Each commit produces one meaningful, testable result.
- No commit depends on unapproved or uncommitted work.
- Each owner stays inside their domain.
- Every commit credibly fits one bounded invocation.
- The sequence can stop safely after any completed commit.
- Runtime overflow has a defined `SPLIT_REQUIRED` recovery path.
- The user can understand the roadmap without reading implementation details.
- The generated protocol and every commit specification are internally consistent and
  machine-validatable.
