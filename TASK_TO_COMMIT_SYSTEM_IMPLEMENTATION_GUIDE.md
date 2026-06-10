# Task-To-Commit Planning System Implementation Guide

**Purpose:** Instruct another model how to design and build a system that converts a
written task or mission into an approved commit protocol and validated commit
specifications.

**System name used in this guide:** Task-To-Commit Planner

**Status:** Implementation blueprint. This document does not authorize implementation.

---

## 1. Foundation Documents

The system must be built from these sources:

### Planning Algorithm

`TASK_TO_COMMIT_PROTOCOL_GUIDE.md`

Defines how to:

- Normalize a mission.
- Extract observable behaviors.
- Assign work types and owners.
- Build dependencies.
- Form candidate commits.
- Split oversized candidates.
- Estimate scope and context.
- Generate a protocol and commit specs.
- Handle approval and runtime scope failure.

### Execution Policy

`MULTI_AGENT_WORKFLOW_REDESIGN_ROADMAP.md`

Defines:

- Hard execution limits.
- One-behavior and one-owner rules.
- Commit-level budget enforcement.
- Context-package limits.
- `SPLIT_REQUIRED`.
- Approval and authority boundaries.
- Non-waivable failures.
- Telemetry, verification, and renumbering principles.

### Output Template

`commit-specs/TEMPLATE.md`

Defines the exact human-readable structure of every generated commit specification.

### Machine Validation

`hooks/validate_commit_spec.py`

Defines the machine-enforced commit-spec rules. The system must call this validator
instead of duplicating its final authority in model prompts.

### Ownership

`AGENTS.md`

Defines:

- Available agents.
- File and domain ownership.
- Forbidden boundaries.
- Reviewer roles.
- Return and handoff contracts.

### Numbering And State

- `commit-protocol.md`
- `project-state.json`

These define the current sequence, completed work, pending work, and next commit.

---

## 2. Authority Order

When sources disagree, apply this order:

1. Enforced hooks and validators.
2. Explicitly approved roadmap decisions.
3. `AGENTS.md` ownership boundaries.
4. `commit-protocol.md` and project state.
5. `commit-specs/TEMPLATE.md`.
6. `TASK_TO_COMMIT_PROTOCOL_GUIDE.md`.
7. Model inference.

The model must report conflicts. It must not silently choose a weaker rule.

---

## 3. System Objective

Given:

- A natural-language mission.
- Repository context.
- Existing architecture and project state.
- Agent ownership rules.
- Execution limitations.

Produce:

1. A normalized mission contract.
2. Clarification questions when required.
3. Observable behavior units.
4. A domain and owner assignment.
5. A dependency graph.
6. Budgeted candidate commits.
7. Split decisions with human-readable reasons.
8. A sequential commit protocol proposal.
9. One template-compliant spec per commit.
10. Validator results.
11. A concise approval package for the user.

The system must not implement the mission.

---

## 4. Core Design Principle

Use the model for semantic reasoning. Use deterministic code for rules.

### Model Responsibilities

- Understand the user's intent.
- Identify ambiguity.
- Extract observable behaviors.
- Classify work.
- Propose dependencies.
- Recommend splits.
- Write contracts and acceptance criteria.
- Explain decisions in human language.

### Deterministic Responsibilities

- Read project state.
- Read agent ownership rules.
- Count files.
- Validate exact paths.
- Calculate budget limits.
- Detect dependency cycles.
- Topologically sort candidates.
- Assign sequential numbers.
- Render Markdown from templates.
- Run `validate_commit_spec.py`.
- Compare filenames, headings, protocol rows, and state.
- Prevent writes before approval.

Do not ask an LLM to enforce arithmetic, numbering, or exact schema consistency when code
can enforce it reliably.

---

## 5. Safety Boundary

The planner has three operational modes:

| Mode | Allowed behavior |
|---|---|
| `analyze` | Read context and produce an in-memory planning record |
| `propose` | Render preview protocol/specs outside authoritative project files |
| `apply` | Write approved protocol/spec changes transactionally |

Default mode is `analyze`.

The system must not:

- Edit application code.
- Invoke implementor agents.
- Change authoritative protocol files before approval.
- Raise execution budgets to make work fit.
- Assign work outside agent ownership.
- Renumber completed commits.
- Accept its own generated plan.
- Continue after a validation or dependency failure.

---

## 6. High-Level Architecture

```text
User Mission
    |
    v
Mission Normalizer
    |
    v
Repository Context Adapter
    |
    v
Behavior Extractor
    |
    v
Domain And Owner Resolver
    |
    v
Dependency Graph Builder
    |
    v
Candidate Commit Builder
    |
    v
Budget And Split Engine
    |
    v
Protocol Numbering Engine
    |
    v
Spec Renderer
    |
    v
Validator And Consistency Gate
    |
    v
Human Approval Package
    |
    v
Transactional Apply
```

Every stage must accept structured input and return structured output.

---

## 7. Recommended Components

### 7.1 Foundation Loader

Loads and fingerprints:

- The roadmap.
- The decomposition guide.
- The template.
- Agent ownership.
- Protocol state.
- Validator version.

Output:

```json
{
  "foundation_version": "sha256-or-git-commit",
  "sources": {
    "roadmap": "MULTI_AGENT_WORKFLOW_REDESIGN_ROADMAP.md",
    "decomposition_guide": "TASK_TO_COMMIT_PROTOCOL_GUIDE.md",
    "template": "commit-specs/TEMPLATE.md",
    "agents": "AGENTS.md",
    "protocol": "commit-protocol.md",
    "state": "project-state.json"
  },
  "limits": {},
  "agents": [],
  "next_commit": 30
}
```

Planning results must record the foundation version used.

### 7.2 Mission Normalizer

Converts natural language into:

```json
{
  "goal": "",
  "users": [],
  "observable_outcomes": [],
  "constraints": [],
  "non_goals": [],
  "unknowns": [],
  "source_text": ""
}
```

If an unknown affects architecture, ownership, security, or acceptance criteria, set the
plan status to `needs_clarification`.

Do not invent product decisions merely to avoid asking a necessary question.

### 7.3 Repository Context Adapter

Provides bounded evidence about existing reality:

- Relevant file paths.
- Existing stubs and contracts.
- Existing tests.
- Completed dependencies.
- Pending overlap.
- Ownership.
- File sizes and symbols.

The adapter should support targeted search and symbol inspection. It should not load the
whole repository into the model.

Every evidence item should include:

```json
{
  "path": "exact/path.py",
  "reason": "Existing route stub",
  "evidence_type": "symbol_search",
  "summary": "Contains four 501 conversation endpoints"
}
```

### 7.4 Behavior Extractor

Converts the mission into atomic observable behaviors.

Each behavior requires:

```json
{
  "id": "B01",
  "statement": "Given X, when Y, then Z",
  "user_value": "",
  "work_type": "",
  "acceptance_signals": [],
  "excluded_behaviors": [],
  "confidence": "high"
}
```

Reject vague behavior statements such as:

- Improve the feature.
- Finish the backend.
- Add the whole workflow.

### 7.5 Ownership Resolver

Maps behavior and exact files to one agent.

Output:

```json
{
  "behavior_id": "B01",
  "owner": "rex",
  "owned_paths": [],
  "cross_domain_dependencies": [],
  "ownership_status": "valid"
}
```

When files cross domains, the resolver should create separate behavior candidates rather
than assigning multiple owners to one commit.

If the repository contains an unowned path, return `ownership_conflict`.

### 7.6 Dependency Graph Builder

Builds a directed acyclic graph using:

- Contract dependencies.
- Data dependencies.
- Verification dependencies.
- Workflow dependencies.
- UI dependencies.

Each edge must contain a reason:

```json
{
  "from": "B01",
  "to": "B02",
  "type": "contract_dependency",
  "reason": "The frontend parser requires the frozen SSE event schema"
}
```

The graph builder must detect:

- Cycles.
- Missing dependencies.
- Dependencies on unapproved work.
- False parallelism caused by shared files.

### 7.7 Candidate Commit Builder

Creates one candidate for each behavior-owner unit.

Required fields:

```json
{
  "candidate_id": "K01",
  "behavior_ids": ["B01"],
  "name": "focused-kebab-name",
  "owner": "rex",
  "work_type": "backend_api",
  "depends_on": [],
  "primary_files": [],
  "changed_files": [],
  "initial_context": [],
  "forbidden_paths": [],
  "estimated_diff_lines": 0,
  "verification_command": "",
  "focused_tests": [],
  "environment_prerequisites": [],
  "not_in_commit": [],
  "risk": "low"
}
```

`behavior_ids` should normally contain one item. Multiple IDs are allowed only when they
describe inseparable parts of one observable contract.

### 7.8 Budget And Split Engine

This component combines deterministic limits with model judgment.

Deterministic checks:

- Primary file count.
- Changed file count.
- Initial context file count.
- Estimated diff lines.
- Owner count.
- Verification command count.
- Exact path requirement.

Semantic checks:

- Multiple independent outcomes.
- Mixed failure modes.
- Mixed domains.
- Discovery risk.
- Large-file risk.
- Several unrelated test surfaces.
- Implausibility within one invocation.

Output:

```json
{
  "candidate_id": "K01",
  "status": "fits",
  "deterministic_violations": [],
  "semantic_risks": [],
  "split_reason": null,
  "replacement_candidates": []
}
```

When uncertain, return `split_required`.

The split engine must explain:

- Why the original candidate was unsafe.
- Which boundary was used.
- What each replacement commit owns.
- How dependencies changed.

### 7.9 Numbering Engine

Runs only after the candidate graph is stable.

Responsibilities:

1. Read the next available integer.
2. Topologically sort candidates.
3. Apply approved priority.
4. Preserve valid parallel groups.
5. Assign sequential IDs.
6. Resolve candidate references to commit IDs.
7. Never renumber completed commits.

Output:

```json
{
  "commits": [
    {
      "commit": "C30",
      "candidate_id": "K01",
      "name": "invocation-record-storage",
      "owner": "adam",
      "depends_on": ["C29"],
      "status": "pending"
    }
  ],
  "parallel_groups": []
}
```

### 7.10 Commit-Spec Renderer

Renders each approved candidate using `commit-specs/TEMPLATE.md`.

The renderer must not allow the model to omit required sections.

Use structured data to populate:

- Heading and metadata.
- Primary Behavior.
- Execution Budget.
- Context.
- Files To Modify Or Add.
- Contract.
- Environment Prerequisites.
- Verification Command.
- Focused Tests.
- Done When.
- Not In This Commit.
- Return Contract.

The template should remain a source file, not be copied permanently into application
code. Template changes should automatically affect future rendering.

### 7.11 Protocol Renderer

Produces a preview of:

- Commit index rows.
- Phase groupings.
- Dependency order.
- Parallel groups.
- Planning notes.

The renderer must preserve completed history and update only the approved pending range.

### 7.12 Validation Gate

For every rendered spec:

1. Write it to an isolated preview workspace.
2. Run `hooks/validate_commit_spec.py`.
3. Capture structured JSON output.
4. Check full-graph consistency.
5. Compare protocol rows, filenames, headings, owners, dependencies, and state.

Validation output:

```json
{
  "status": "valid",
  "spec_results": [],
  "graph_results": [],
  "consistency_results": [],
  "blocking_issues": []
}
```

A validator failure returns the plan to the candidate or split stage. It never proceeds
to approval as a valid plan.

### 7.13 Approval Package Builder

The user-facing package should be concise.

Include:

- Mission summary.
- Important assumptions.
- Number of proposed commits.
- Phase table.
- Commit table with behavior, owner, files, estimate, and dependency.
- Split explanations.
- Parallel groups.
- Risks or unresolved decisions.
- Validation status.
- Exact files that will change if approved.

Do not force the user to read every full spec before understanding the plan.

The full specs remain available for inspection.

### 7.14 Transactional Apply Engine

Runs only after explicit approval.

It must update together:

- `commit-protocol.md`.
- Pending `commit-specs/commit-NN.md` files.
- `project-state.json` when required.
- Dependencies and handoffs.
- Any approved roadmap references.

Apply process:

1. Confirm the foundation version has not changed.
2. Re-read state and next commit.
3. Detect concurrent modifications.
4. Create temporary output.
5. Validate the complete proposed graph.
6. Move all approved files into place transactionally.
7. Run validation again on authoritative files.
8. Produce a human-readable change summary.

On failure, leave authoritative planning files unchanged.

---

## 8. Canonical Planning Record

Store the complete intermediate plan in JSON.

Suggested location:

```text
.planning/task-to-commit/<plan-id>/plan.json
```

Minimum shape:

```json
{
  "schema_version": 1,
  "plan_id": "uuid",
  "status": "awaiting_user",
  "created_at": "ISO-8601",
  "foundation_version": "",
  "mission": {},
  "evidence": [],
  "behaviors": [],
  "ownership": [],
  "dependency_edges": [],
  "candidates": [],
  "split_decisions": [],
  "protocol": [],
  "parallel_groups": [],
  "rendered_specs": [],
  "validation": {},
  "approval": {
    "status": "awaiting_user",
    "approved_by": null,
    "approved_at": null
  }
}
```

Markdown is a rendered artifact. JSON is the planning source of truth for the system.

---

## 9. State Machine

Use explicit states:

```text
received
  -> analyzing
  -> needs_clarification
  -> decomposing
  -> split_required
  -> rendering
  -> validating
  -> awaiting_user
  -> approved
  -> applying
  -> applied
```

Failure states:

```text
ownership_conflict
dependency_conflict
validation_failed
foundation_changed
apply_failed
```

Rules:

- `needs_clarification` returns to `analyzing`.
- `split_required` returns to `decomposing`.
- `validation_failed` returns to the earliest responsible stage.
- `awaiting_user` cannot transition to `applying`.
- Only explicit user approval creates `approved`.
- A changed foundation invalidates stale approval.

---

## 10. Model Prompt Contract

The planning model should receive:

- The normalized mission.
- Relevant repository evidence only.
- Agent ownership summary.
- Locked budget values.
- Decomposition rules.
- Current candidate graph.
- Required structured output schema.

The model should not receive:

- Entire repository contents.
- Full historical telemetry unless relevant.
- Unrelated commit specs.
- Permission to modify files.
- Permission to raise limits.

Require structured output and validate it before use.

The prompt should state:

1. Produce observable behaviors, not epics.
2. Assign one owner per candidate.
3. Use exact known paths.
4. Mark uncertain paths as unresolved instead of inventing them.
5. Prefer splitting when fit is uncertain.
6. Explain every split in plain language.
7. Do not assign final commit numbers.
8. Do not claim approval.

---

## 11. Clarification Policy

Ask the user only when the answer materially changes:

- Product behavior.
- Architecture.
- Security.
- Ownership.
- External compatibility.
- Acceptance criteria.
- Whether existing data may be migrated or replaced.

Do not ask about decisions discoverable from the repository.

When clarification is required, present:

- The missing decision.
- Why it affects decomposition.
- The smallest set of choices.
- The recommended option and tradeoff.

---

## 12. Budget Policy

Use the roadmap's hard limits:

```yaml
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

Plan below the limits:

- Prefer 2-3 changed files.
- Prefer 200-280 estimated lines.
- Prefer 3-5 context files.
- Reserve capacity for unexpected corrections.

No ordinary plan may create a bootstrap exception.

Exceptions require a separately approved governance decision and exact machine-validated
scope.

---

## 13. Split Strategy

Apply split checks in this order:

1. Observable behavior.
2. Ownership.
3. Dependency or contract boundary.
4. Database versus application behavior.
5. Backend versus frontend.
6. Transport versus presentation.
7. Storage versus aggregation versus dashboard.
8. Implementation versus evaluation.
9. File, diff, context, and verification limits.
10. Agent-capacity judgment.

Avoid arbitrary splits such as "first half of file" and "second half of file."

Every split must create useful, independently testable commits.

---

## 14. Validation Strategy

Use three levels:

### Level 1: Structural

- JSON schema.
- Required fields.
- Exact paths.
- Numeric limits.
- One owner.
- One verification command.

### Level 2: Repository Consistency

- Files exist or are explicitly marked new.
- Owners match paths.
- Dependencies exist.
- No cycles.
- Commit numbers are sequential.
- Protocol, state, headings, and filenames agree.

### Level 3: Semantic Review

- One observable behavior.
- Acceptance criteria prove that behavior.
- Tests match the contract.
- Exclusions are explicit.
- The candidate credibly fits one invocation.
- The sequence can stop safely after each commit.

All three levels must pass before user approval.

---

## 15. Test Plan For The Planner

### Mission Normalization

- Clear mission produces no unnecessary questions.
- Ambiguous mission enters `needs_clarification`.
- Non-goals are preserved.

### Behavior Extraction

- One epic becomes several observable behaviors.
- Vague outputs are rejected.
- Independent outcomes are not merged.

### Ownership

- Backend and frontend work split correctly.
- Nova-owned service files do not route to Rex.
- Unowned paths produce a blocking conflict.

### Dependencies

- Contract-before-consumer order is preserved.
- Cycles are rejected.
- Independent owned commits may form a parallel group.

### Budgeting

- Five changed files trigger a split.
- Three primary files trigger a split.
- A 351-line estimate fails.
- Multiple verification surfaces trigger semantic review.
- Limits cannot be raised by model output.

### Rendering

- Every spec follows `commit-specs/TEMPLATE.md`.
- Human Summary and telemetry Return Contract remain present.
- Exact filenames and headings match assigned numbers.

### Validation

- Invalid specs never reach `awaiting_user`.
- Validator JSON is preserved.
- Full pending graph validates.

### Approval

- Preview requires no authoritative writes.
- Apply is blocked without explicit approval.
- Foundation changes invalidate stale approval.

### Transactional Apply

- Partial failure changes no authoritative file.
- Renumbering has no filename collisions.
- Completed commit history remains unchanged.

---

## 16. Recommended Delivery Phases

### Phase 1: Read-Only Analyzer

Build:

- Foundation loader.
- Mission normalizer.
- Repository context adapter.
- Behavior extractor.
- Ownership resolver.
- JSON planning record.

Output only analysis and clarification questions.

### Phase 2: Decomposition Engine

Build:

- Dependency graph.
- Candidate builder.
- Budget and split engine.
- Human-readable split explanations.

Output an unnumbered candidate plan.

### Phase 3: Protocol And Spec Preview

Build:

- Numbering engine.
- Protocol renderer.
- Spec renderer.
- Isolated preview workspace.

No authoritative writes.

### Phase 4: Validation And Approval

Build:

- Validator integration.
- Full-graph consistency checks.
- Approval package.
- Approval state.

### Phase 5: Transactional Apply

Build:

- Concurrent-change detection.
- Transactional renumbering and writes.
- Post-apply validation.
- Audit record.

### Phase 6: Runtime Feedback

Build:

- Import of implementor Human Summary and telemetry.
- Import of `SPLIT_REQUIRED`.
- Replanning unfinished scope.
- Comparison of estimated versus actual scope.

The system should become write-capable only after read-only planning and validation are
proven reliable.

---

## 17. Suggested Interfaces

Possible command-line interface:

```powershell
python planner.py analyze --task task.md
python planner.py propose --plan <plan-id>
python planner.py validate --plan <plan-id>
python planner.py approve --plan <plan-id>
python planner.py apply --plan <plan-id>
```

Possible API:

```text
POST /plans
POST /plans/{id}/clarifications
POST /plans/{id}/decompose
POST /plans/{id}/validate
POST /plans/{id}/approve
POST /plans/{id}/apply
GET  /plans/{id}
GET  /plans/{id}/artifacts
```

Approval endpoints must require explicit authenticated user action.

---

## 18. Auditability

For every plan, retain:

- Original task text.
- Foundation version.
- Repository evidence used.
- Model outputs.
- Deterministic validation results.
- Split reasons.
- Numbering decisions.
- User clarifications.
- User approval.
- Files written during apply.

The system must make it possible to answer:

- Why was this mission split this way?
- Why was this agent selected?
- Which rule caused a split?
- What changed after clarification?
- Which foundation version approved the plan?
- Did actual execution exceed the estimate?

---

## 19. Failure Policy

Fail closed when:

- Foundation files cannot be read.
- Ownership is ambiguous.
- Required repository evidence is missing.
- The dependency graph contains a cycle.
- A candidate exceeds a hard limit.
- A generated spec fails validation.
- Protocol, state, and specs disagree.
- Approval is absent or stale.
- Authoritative files changed after approval.

Failure output must include:

- Status.
- Stage.
- Human-readable explanation.
- Technical rule or evidence.
- Allowed next action.

Do not convert failures into warnings to continue.

---

## 20. Definition Of Done

The Task-To-Commit Planner is complete when:

- A written mission becomes a structured planning record.
- Ambiguity is surfaced before commits are generated.
- Behaviors, owners, dependencies, and splits are explainable.
- Every candidate is budgeted against the roadmap limits.
- Every generated spec follows the canonical template.
- Every generated spec passes the repository validator.
- The complete pending graph is internally consistent.
- No authoritative planning file changes without explicit approval.
- Approved changes apply transactionally.
- Runtime `SPLIT_REQUIRED` can safely return unfinished scope to planning.
- A user can understand the proposed protocol from a concise summary.

---

## 21. Instructions To The Implementing Model

When building this system:

1. Treat the foundation files as executable policy, not background reading.
2. Build structured intermediate representations before Markdown generation.
3. Keep semantic reasoning separate from deterministic enforcement.
4. Start read-only.
5. Add one component and its tests at a time.
6. Use the same micro-commit limits the finished planner will enforce.
7. Validate generated outputs with the real repository validator.
8. Preserve human approval as a hard boundary.
9. Never solve planning overflow by increasing agent budgets.
10. Keep every decision explainable to a developer without requiring raw model logs.
