# Commit 29A - `preflight-score-engine` - Adam

**Phase:** Workflow Preflight
**Owner:** adam
**Depends on:** C29
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Build, score, and persist a deterministic commit-readiness report as a standalone hook
script, independent of the delegation pipeline that will consume it.

---

## Semantic Fit Review

- **Atomic outcome:** One script converts existing planning evidence into a repeatable, persisted proceed/block report for any commit ID.
- **Failure boundary:** It evaluates and persists readiness only; it does not call, edit, or gate `prepare_agent_delegation.py`.
- **Budget rationale:** One new primary file plus its test file, reusing existing validators and the context engine with no new contract surface to reverse-engineer.

---

## Execution Budget

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

bootstrap_exception:
  reason: "greenfield-module — new hook script plus its full test suite from scratch, second authorized invocation after a zero-code SPLIT_REQUIRED"
  max_tool_calls: 28
  max_expansions: 2
  max_implementor_tokens: 55000
  max_total_tokens: 70000
  max_agent_invocations: 1
  max_estimated_diff_lines: 1200
```

This `bootstrap_exception` is the **greenfield-module budget profile**, authorized by Eran
for C29A only. It does not change the default 18-call/45,000-token/350-diff-line profile
used for ordinary (non-greenfield) commits. `validate_commit_spec.py` validates these
fields against the greenfield ceilings and returns the merged effective budget; running
`prepare_agent_delegation.py` propagates that effective budget into `hooks/tool_cap.json`
automatically — `limits.max_tool_calls` becomes 28, `limits.max_implementor_tokens` 55000,
`limits.max_total_tokens` 70000, and `limit` 28 (`limits.max_expansions` and
`limits.max_agent_invocations` are unchanged). No manual `tool_cap.json` editing is
required or performed. `max_estimated_diff_lines: 1200` was added retroactively
(2026-06-11) after C29A's implementation (a from-scratch scoring engine plus its 13-case
test suite, ~1080 lines) exceeded the locked 350-line cap; `verify_constraints.py`'s
actual-scope check reads this override from `validate_commit_spec`'s effective budget.

### Greenfield Invocation Protocol (C29A only)

- The "Discovery Notes" section below is **authoritative**. Do not re-read
  `validate_commit_spec.py` or `context_engine.py` to confirm these contracts, and do not
  run `Glob`/directory scans to confirm files exist or don't exist — trust this spec.
- Implementation must begin by call 6: either `hooks/preflight_commit.py` or
  `hooks/tests/test_preflight_commit.py` must exist (created or with content written) by
  then.
- At call 22, report remaining acceptance criteria and budget status.
- By call 26, finish or return `SPLIT_REQUIRED`.
- Call 28 is a hard stop.

---

## Context

```yaml
primary_files:
  - hooks/preflight_commit.py
initial_context:
  - hooks/validate_commit_spec.py
forbidden:
  - backend/
  - frontend/
  - hooks/prepare_agent_delegation.py
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/preflight_commit.py` | new | Build, score, persist, and print a deterministic readiness report for one commit |
| `hooks/tests/test_preflight_commit.py` | new | Prove scoring, blockers, persistence, and compact output |

---

## Discovery Notes (carried over from the C29A research-only invocation)

These contracts already exist and should be called directly, not re-derived:

- `validate_commit_spec.validate_commit_spec(repo_root, commit, expected_owner) -> dict`
  returns `{"status": "valid"|"split_required", "commit", "owner", "budget", "dependencies",
  "planned_changed_files", "violations": [...]}`. `status != "valid"` is a hard block.
- `validate_commit_spec.validate_pending_graph(repo_root) -> dict` returns
  `{"status", "pending_commits", "spec_results", "violations": [...]}`. `status != "valid"`
  is a hard block.
- `validate_commit_spec.protocol_entries(repo_root) -> dict[str, {"name", "owner", "status"}]`
  keyed by the canonical commit ID as returned by `commit_key()` (e.g. `"C29A"`, always
  with the `C` prefix and zero-padded number); `owner` is the lowercase agent id.
- `hooks/agent-config.json` has the shape `{"agents": {"<email>": {"name", "role",
  "domains": [...]}, ...}, "universal_allowed": [...], "initialized": true}`. Find the
  entry whose `name.lower() == agent` (the `--agent` argument, e.g. `"adam"`). Map
  `role` to a display domain for the approval card: `devops -> DevOps`, `backend -> Backend`,
  `frontend -> Frontend`, `ai-engineer -> AI/ML`, `orchestrator -> Orchestration`.
- `context_engine.load_rules(path) -> dict` is `json.loads(path.read_text())` — load
  `repo_root / "hooks" / "context_rules.json"` directly, no parsing logic needed.
- `context_engine.ContextPackageBuilder(repo_root, rules, graph_path=None,
  mode="preflight").build(commit, agent) -> dict` returns `{"files": [...],
  "excluded_candidates": [...], "forbidden_edits": [...], "expansion_triggers": [...],
  "unresolved": [...], "budget": {...}}`. Pass `graph_path=None` (it derives the cache
  path from `rules["graph"]["cache_path"]` itself). `mode` is stored verbatim as a label
  and does not change behavior. An empty `excluded_candidates` and zero `unresolved`
  items are required for a clean context-package-integrity score; a non-empty
  `expansion_triggers` list is a non-blocking readiness deduction, not a hard block.

---

## Contract

The script accepts `--commit <ID> --agent <agent-id> [--json]` and reuses the validators,
protocol/state readers, agent-config map, and `ContextPackageBuilder` listed above. It
writes full diagnostics to `.context/preflight/C<ID>.json` and prints the compact result:

```json
{
  "commit": "C30",
  "score": 92,
  "owner": {"id": "adam", "name": "Adam", "domain": "DevOps"},
  "goal": "Store separate invocation telemetry records.",
  "files": [
    {"action": "edit", "path": "hooks/context_telemetry.py"}
  ],
  "blocking_violations": [],
  "warnings": ["Docker availability was not confirmed"],
  "decision_required": false,
  "proceed": true,
  "report_path": ".context/preflight/C30.json"
}
```

`goal` is the first sentence of the spec's `Primary Behavior` section. `files` comes from
the spec's `Files To Modify Or Add` table, mapping its `Type` column (`new`/`add` -> `add`,
`edit` -> `edit`, `delete`/`remove` -> `delete`).

The module exposes an importable `evaluate(repo_root, commit, agent) -> dict` function
returning exactly the compact result shown above (after persisting the full report as a
side effect). The CLI is a thin wrapper: it calls `evaluate(...)` and prints
`json.dumps(result)` with `--json`, or a human-readable rendering of the same fields
without it. C29B imports `evaluate` directly to gate delegation.

### Score categories (sum to 100, all hard-blocking)

| Category | Points | Pass condition |
|---|---|---|
| Specification validity | 15 | `validate_commit_spec(...).status == "valid"` |
| Pending graph validity | 10 | `validate_pending_graph(repo_root).status == "valid"` |
| Ownership match | 10 | spec owner equals `commit-protocol.md` owner and `project-state.json` `next_commit_assignee` |
| Scope/forbidden compliance | 10 | every planned changed file passes `owner_paths` and matches none of the spec's `forbidden` entries |
| Context package integrity | 15 | `ContextPackageBuilder.build()` does not raise, and `excluded_candidates`/`unresolved` are both empty, and selected files/chars are within `validation["budget"]` limits |
| Verification command present | 10 | non-empty `Verification Command` section containing one recognized, concrete invocation (see below) |
| Acceptance criteria present | 10 | non-empty `Done When` and (`Focused Tests` or `Required Tests`) sections |
| Dependencies satisfied | 20 | every commit in `Depends on` has `done`/`✅ done` status in `commit-protocol.md` |

Each category is all-or-nothing: failing it both zeroes its points and raises the
matching hard violation below. When every category passes, `hard_points = 100`.

#### Recognized verification commands

The `Verification Command` section's fenced code block is recognized (and scores the
full 10 points) when its content, stripped of leading/trailing whitespace, matches at
least one of:

- `pytest ...` or `python -m pytest ...`
- A Docker-wrapped pytest invocation, e.g. `docker compose run --rm <service> ... pytest ...`
  or `docker compose exec <service> ... pytest ...`
- `npm test` or `npm run test ...`
- `python <script>.py ...` (a concrete `.py` script path)
- A PowerShell script invocation, e.g. `.\<script>.ps1 ...` or `pwsh ./<script>.ps1 ...`

Any other non-empty content that names a concrete, runnable command (no placeholders such
as `<...>`, `TODO`, or wildcards) scores the full 10 points as a fallback match. Only an
empty/missing section, or one containing only placeholders/wildcards, loses these points.

### Non-blocking readiness deductions

These never set `blocking_violations` and never affect which hard categories pass; they
are subtracted from `hard_points` to produce `score`. Each triggered deduction is echoed
verbatim in `warnings`, naming the deduction and the evidence.

| Deduction | Amount | Cap | Trigger |
|---|---|---|---|
| Context expansion warnings | 5 per distinct trigger | 10 | `expansion_triggers` from the context package is non-empty |
| Environment prerequisite tooling | 5 per unavailable tool | 10 | A recognized tool name (below) appears in `Environment Prerequisites` and `shutil.which(...)` returns `None` for it |
| Dependency artifact existence | 5 per missing file | 10 | A `new`/`edit` file from a `Depends on` commit's `Files To Modify Or Add` table does not exist on disk |
| Verification tool availability | 10 | 10 | The `Verification Command`'s primary executable is not found via `shutil.which(...)` |

`score = max(0, hard_points - sum(triggered deductions))`.

#### Recognized environment-prerequisite tools

Case-insensitive whole-word matches against the `Environment Prerequisites` section text,
each checked via `shutil.which`: `docker`, `npm`, `node`, `pytest`, `python`,
`pwsh`/`powershell` (checked as `pwsh`), `ollama`, `psql`/`postgres` (checked as `psql`),
`alembic`, `git`. Each distinct recognized tool that resolves to `None` deducts 5 points,
capped at 10 for this row regardless of how many tools are missing.

#### Dependency artifact existence

For each commit listed in `Depends on`, load `commit-specs/commit-<id>.md` (lowercase,
no `C` prefix) and read its `Files To Modify Or Add` table. For every row whose `Type` is
`new` or `edit`, check that the path exists relative to `repo_root`. Each missing path
deducts 5 points (cap 10), reported as a warning naming the dependency commit and the
missing path. A dependency spec file that cannot be found is skipped (not a deduction) —
absence of the spec itself is covered by "Dependencies satisfied" above.

#### Verification tool availability

Resolve the **host executable** of the `Verification Command` block, then check it with
`shutil.which(...)`. If not found, deduct 10 points once.

Resolution steps:

1. Split the block on `;` and newlines into statements. Drop any leading statements whose
   first token is a shell built-in with no standalone executable (`cd`, `pushd`, `popd`,
   `set`, `export`, or a `$env:...=...` assignment). Use the last remaining statement
   (e.g. `cd frontend; npm test -- --run` -> `npm test -- --run`).
2. Tokenize that statement on whitespace.
3. If the first two tokens are `docker compose`, or the first token is `docker-compose`,
   the host executable is satisfied if `shutil.which("docker")` **or**
   `shutil.which("docker-compose")` resolves — do not descend into compose flags
   (`run`, `--rm`), the service name, `uv`, or the wrapped command (e.g.
   `docker compose run --rm backend uv run pytest ... -q` -> checks `docker`/`docker-compose`,
   never `uv` or `pytest`).
4. Else if the first token is `powershell`, `pwsh`, `python`, `pytest`, or `npm`, the host
   executable is that token — check it directly (ignore all following flags, subcommands
   such as `npm test`, and script paths, e.g.
   `powershell -ExecutionPolicy Bypass -File scripts/x.ps1` -> `powershell`;
   `npm test -- --run` -> `npm`; `python -m pytest` -> `python`).
5. Else if the first token ends in `.ps1` (a direct `.\script.ps1` or `./script.ps1`
   invocation with no interpreter prefix), the host executable is `pwsh`.
6. Else the host executable is the first token with any leading `./` or `.\` stripped.

A statement consisting only of a shell built-in with nothing after it is not a valid
verification command and is handled by the "Recognized verification commands" hard
violation, not this deduction.

### Hard violations (block regardless of score)

```text
proceed = score >= 80 AND blocking_violations is empty
```

Hard violations come only from the eight scored categories above — never from the
non-blocking readiness deductions:

- Invalid commit specification or pending dependency graph (either validator's `status != "valid"`).
- Missing dependency (a `Depends on` commit not `done`), ownership mismatch, or a planned
  file that fails `owner_paths` or matches a `forbidden` entry.
- `ContextPackageBuilder.build()` raising, or `excluded_candidates`/`unresolved` non-empty,
  or selected files/chars exceeding `validation["budget"]` limits.
- Missing, empty, placeholder-only, or wildcard-only `Verification Command` section (see
  "Recognized verification commands" — a `pytest`, Docker-wrapped pytest, `npm test`,
  Python script, or PowerShell script invocation, or any other concrete runnable command,
  is sufficient; the command is not required to be `pytest`).
- Missing or empty `Done When`, or missing both `Focused Tests` and `Required Tests`.

Each blocking violation in the persisted report names the rule, the evidence, and a
plain-language repair direction. Non-blocking readiness deductions never appear in
`blocking_violations` — only in `warnings` and the score breakdown. The score measures
readiness evidence, not predicted implementation correctness.

### Persistence and determinism

`.context/preflight/C<ID>.json` contains the full category breakdown (points awarded,
points possible, deductions with reasons), the raw validator results, the context
package, `blocking_violations`, `warnings`, and the compact result shown above.
Re-running the script for the same commit and agent against an unchanged repository
produces an identical score, identical `blocking_violations`, and an identical
`report_path` — no timestamps or non-deterministic fields affect `score`,
`blocking_violations`, `proceed`, or `files`.

---

## Environment Prerequisites

- Python hook test environment.
- Existing C29 validator, context engine, ownership configuration.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_preflight_commit.py -q
```

---

## Focused Tests

- Score 80 or greater with no blocker yields `proceed: true`.
- A fixture with all eight hard categories passing but enough non-blocking readiness
  deductions triggered (e.g. an unavailable environment-prerequisite tool, a missing
  dependency artifact, an expansion-trigger warning, and an unavailable verification
  tool — totaling more than 20 points) yields `score < 80`, `blocking_violations == []`,
  and `proceed: false`, with each deduction itemized in `warnings`.
- A hard violation (e.g. invalid pending graph, ownership mismatch, missing verification
  command, missing `Done When`) yields `proceed: false` even when `hard_points` would
  otherwise be 100, and is listed in `blocking_violations`, not just `warnings`.
- Identical inputs (same commit, agent, and repository state) produce an identical score,
  `blocking_violations`, and `report_path` across two runs.
- `.context/preflight/C<ID>.json` contains the full category breakdown (hard categories
  and readiness deductions separately) while stdout remains the compact JSON shape above.
- Compact output contains `owner.name`, `owner.domain`, `goal`, `files` with actions, and
  exact warning text.
- A non-empty `expansion_triggers` list appears verbatim in `warnings` and deducts from
  `score` without setting `blocking_violations`.
- An `Environment Prerequisites` section naming a tool not on `PATH` (mocked via
  `shutil.which` returning `None`) deducts 5 points per distinct unavailable tool (cap
  10) and is echoed in `warnings`, without setting `blocking_violations`.
- A `Depends on` commit whose `Files To Modify Or Add` lists a `new`/`edit` file that does
  not exist on disk deducts 5 points per missing file (cap 10) and names the commit and
  path in `warnings`, without setting `blocking_violations`.
- A `Verification Command` whose primary executable is not found via `shutil.which`
  deducts 10 points and is named in `warnings`, without setting `blocking_violations` or
  triggering the verification-command hard violation (the section itself is still
  present and concrete).
- C33's exact verification command, `docker compose run --rm backend uv run pytest
  tests/api/test_documents.py -q`, resolves its host executable to `docker` (or
  `docker-compose`) — never `uv` or `pytest` — for the availability check.
- C65's exact verification command, `cd frontend; npm test -- --run`, drops the leading
  `cd frontend` built-in statement and resolves its host executable to `npm`.
- C76's exact verification command, `powershell -ExecutionPolicy Bypass -File
  scripts/smoke_policy_chat.ps1`, resolves its host executable to `powershell`, ignoring
  `-ExecutionPolicy Bypass -File` and the script path.
- A `Verification Command` section containing a Docker-wrapped pytest invocation, an
  `npm test` invocation, a `python <script>.py` invocation, or a `.ps1` PowerShell script
  invocation each score the full 10 points and do not trigger the verification-command
  hard violation.

Use temporary fixture repositories (a minimal `commit-protocol.md`, `project-state.json`,
and one or more `commit-specs/commit-*.md` files under `tmp_path`) so these tests do not
depend on the live pending-commit range.

---

## Done When

- [ ] The report is deterministic and uses only existing local evidence.
- [ ] The eight hard categories total 100 and each failure is both a point loss and a
      listed hard violation.
- [ ] Non-blocking readiness deductions (expansion warnings, environment-prerequisite
      tooling, dependency artifact existence, verification tool availability) can drive
      `score` below 80 with zero `blocking_violations`, and each is explained in `warnings`.
- [ ] Hard violations override the threshold regardless of `score`.
- [ ] `.context/preflight/C<ID>.json` is written with full diagnostics on every run.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C32.

---

## Not In This Commit

- Editing or gating `hooks/prepare_agent_delegation.py` (C29B).
- Dashboard presentation of preflight history (C29C).
- LLM-based review or a second agent invocation.
- Changing C30-C76 feature behavior.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. Include the
score categories, hard-block rules exercised by tests, and confirmation that
`.context/preflight/C<ID>.json` is written deterministically. Per the greenfield
invocation protocol above: implementation must begin by call 6, report budget status and
remaining acceptance criteria at call 22, and if completion is not credible by call 26,
stop and return `SPLIT_REQUIRED`.
