# Client Dashboard Observability Design

> Status: Approved design direction, implementation not started
> Date: 2026-06-14
> Purpose: Define the client-facing observability contract before changing capture,
> metrics, token accounting, or dashboard rendering.

## Product Requirement

The constraint dashboard is part of the package delivered to the client. It is not
only an internal debugging page. It must let a client navigate the codebase and verify
what Claude and delegated agents changed, how the work was executed, and how efficiently
tokens and tools were used.

The dashboard is an evidence renderer. It must display facts derived from repository
artifacts and runtime telemetry without inventing, estimating, or semantically inferring
missing measurements.

## Problem Statement

The current dashboard represents delegated execution better than Claude-direct
execution:

- Delegated commits have a context package, agent self-report, hook telemetry, and
  orchestrator telemetry.
- Claude-direct commits deliberately have no delegated-agent package or self-report.
- Git-derived changed files are persisted for direct commits, but graph overlays are
  currently built from delegated live packages only.
- Claude tool telemetry begins during post-implementation inspection rather than before
  direct implementation, so direct reads, writes, searches, and commands may be absent.
- Direct token usage is not currently measured.

This creates a client-facing observability gap because Claude-direct is the default
execution mode used to reduce invocation and token overhead.

## Decision Principles

1. Deterministic local functions collect, reconcile, calculate, and render facts.
2. Model or agent invocation is not part of normal dashboard operation.
3. Agents are used only for an explicitly requested semantic explanation or conclusion
   that cannot be derived mechanically.
4. Git is authoritative for committed file changes.
5. Commit specifications are authoritative for planned scope and domain ownership.
6. Persisted hook telemetry is authoritative for measured runtime activity.
7. Token records or session usage events are authoritative for token consumption.
8. Missing data remains missing and is never converted to zero or silently estimated.
9. Every displayed metric exposes its source and completeness.
10. Identical source artifacts must produce identical dashboard output.

## Canonical Commit Evidence Model

Every commit needs one normalized observability record regardless of execution mode.
The record separates accountability, execution, file evidence, measurements, and
provenance.

### Identity

- `commit`: stable commit identifier.
- `owner`: domain owner from the approved commit specification.
- `executor`: `claude` for direct execution or the invoked agent for delegation.
- `execution_mode`: `claude-direct` or `delegated`.
- `task_kind`: deterministic classification from the commit specification when present.

Owner and executor are intentionally separate. A Claude-direct commit owned by Rex is
displayed as `Owner: Rex`, `Executor: Claude`, not as a Rex invocation.

### File Evidence

- `planned_files`: parsed from `Files To Modify Or Add` in the commit specification.
- `selected_context_files`: delegated package files, when a package exists.
- `read_files`: measured telemetry only.
- `written_files`: measured telemetry only.
- `expanded_files`: measured delegated context expansion only.
- `committed_files`: derived from Git.
- `change_types`: added, modified, renamed, deleted, or type-changed, derived from Git.

These sets must remain distinct. A selected file was not necessarily read, a written
file was not necessarily committed, and a committed file was not necessarily present in
a delegated context package.

### Execution Measurements

- Tool calls by execution scope.
- Reads, writes, searches, and commands.
- Verification and test commands.
- Token counts by executor and invocation kind.
- Input, output, cache-creation, and cache-read tokens when the source provides them.
- Repair and review invocation usage, stored separately from primary implementation.
- Declared budgets and deterministic utilization ratios.

### Provenance

Every field or metric carries one of these source states:

- `git-derived`
- `spec-derived`
- `hook-measured`
- `self-reported`
- `token-record-derived`
- `reconstructed`
- `not-captured`
- `not-applicable`

`Reconstructed` means the fact was recovered deterministically from existing primary
artifacts after the original run. It does not mean estimated.

## Data Purity Rules

The dashboard must not infer:

- files read when no read telemetry exists;
- token counts from tool calls, elapsed time, or changed lines;
- executor identity from domain ownership;
- success quality from low token usage;
- intent from filenames or diff contents;
- agent activity when no agent invocation occurred;
- zero usage from an absent measurement.

Derived values are allowed only when every input exists and the formula is fixed. For
example:

```text
budget utilization = measured tokens / declared token budget
tokens per changed file = measured tokens / Git-derived changed-file count
cache reuse ratio = cache-read tokens / total input-side tokens
```

If any required input is unavailable, the derived value is `Unavailable`.

## Deterministic Processing Architecture

Normal dashboard generation must follow this local pipeline:

```text
Commit spec + Git + hook telemetry + token records
                         |
                         v
             Deterministic normalizer
                         |
                         v
              Canonical commit record
                         |
               +---------+---------+
               |                   |
               v                   v
       Reconciliation checks   Dashboard renderer
```

The normalizer and renderer must not call an LLM, invoke an agent, or require a semantic
summary. Existing human-written spec titles and summaries may be displayed as source
content, clearly identified as spec-derived.

## Claude-Direct Capture Decision

Claude execution telemetry must open immediately after approval and before the first
implementation read, search, edit, or command. It must close only after verification
finishes.

This changes the meaning of the existing Claude scope from post-agent orchestration
only to the complete Claude execution scope for direct commits. Delegated commits retain
two scopes:

- delegated implementor activity;
- Claude review and verification activity.

The storage schema may retain legacy `orchestrator` field names for compatibility, but
the dashboard language should use `Claude execution` or `Claude review` according to the
execution mode.

Current commits must fail closed at finalization when their required execution telemetry
scope was never finalized. Historical commits remain renderable with explicit
`not-captured` states.

## Token Accounting Decision

Token observability must add zero model calls and zero model tokens.

Token usage will be collected from already-produced session usage events or persisted
token records and aggregated by local code. The system must:

- separate Claude-direct, delegated implementor, review, and repair usage;
- exclude delegated subagent usage from Claude totals when it is already recorded
  separately;
- retain raw input/output/cache categories when available;
- persist partial progress so a rate-limit interruption does not erase measurements;
- record source version and completeness because transcript formats may change;
- never estimate tokens when the source is unavailable.

### Token Tradeoff

Session transcript parsing can provide the missing Claude usage, but transcript format
is not a guaranteed stable public contract. The accepted tradeoff is to isolate parsing
behind a versioned adapter, preserve raw-source provenance, fail visibly on unknown
formats, and keep token capture independent from core file observability.

Token instrumentation must therefore be implemented and validated as a separate phase.
A parser failure may make token metrics unavailable, but must not corrupt file evidence
or prevent deterministic graph rendering.

## Efficiency Presentation

The dashboard should show facts and transparent ratios rather than a single opaque
efficiency score.

Candidate measurements include:

- declared token budget and measured utilization;
- total, input, output, cache-read, and cache-creation tokens;
- Claude versus delegated-agent token usage;
- primary, review, and repair usage;
- tool calls;
- planned, read, written, and committed file counts;
- changed lines;
- tokens per committed file;
- tokens per changed line;
- tool calls per committed file;
- cache reuse ratio;
- first-pass versus repair activity;
- delegation overhead when delegation occurred.

These values provide optimization evidence but are not standalone quality judgments.
A security-sensitive change may correctly consume more reasoning than a large mechanical
edit. Quality remains established by tests, verification, review, and acceptance
criteria.

## Rate-Limit Protection

Observability must not accelerate session exhaustion. The implementation will:

- perform all aggregation locally;
- avoid additional agent invocations;
- update only the active commit record during normal operation;
- cache the codebase dependency graph;
- rebuild graph structure only when relevant files change;
- render at controlled lifecycle points rather than after each tool event;
- use compact append-only events or bounded summaries;
- avoid rereading historical transcripts through a model;
- expose warning and hard budget thresholds using deterministic comparisons.

Warnings may be displayed at configured utilization thresholds, but they must not claim
that a rate limit will occur unless that limit is supplied by an authoritative source.

## Graph Rendering Decision

Commit overlays will be generated from canonical commit records, not solely from
delegated live packages.

Every commit overlay must show:

- owner;
- executor;
- execution mode;
- planned files;
- measured read and written files;
- Git-derived committed files and change type;
- delegated selected context and expansions when applicable;
- provenance and completeness.

New and deleted files must remain navigable even when absent from the cached dependency
graph. Actual committed files receive the strongest visual emphasis. Context selection
and reads are supporting evidence and must not visually imply a committed change.

## Historical Backfill

Historical records will be backfilled only from trustworthy existing artifacts:

- Git for committed files and change types;
- commit specifications for planned files and owners;
- existing telemetry for measured calls and file activity;
- existing token records for measured delegated usage.

Historical reads, writes, calls, or tokens that were never captured remain
`not-captured`. Backfill must not fabricate equivalent activity from the final diff.

## Semantic Explanation Boundary

The core dashboard does not need an agent to explain measurements.

An optional explanation feature may invoke an agent only when a user explicitly asks a
semantic question such as why a commit consumed unusually high tokens or what an
architectural change means. Such output must:

- be labeled `AI-generated explanation`;
- cite the factual records used as input;
- remain separate from measured fields;
- be cached by input hash;
- never alter canonical evidence;
- never be required to load, navigate, or reconcile the dashboard.

## Tradeoffs Accepted

### Richness Versus Purity

We prefer an explicit unavailable state over a plausible but inferred value. The
dashboard may look less complete for old commits, but its claims remain defensible.

### Capture Coverage Versus Runtime Overhead

Capturing compact local tool events and usage counters adds small disk and CPU overhead.
This is accepted because it adds no model tokens and provides complete future evidence.

### Compatibility Versus Clean Naming

Legacy fields such as `orchestrator` may remain in persisted records during migration.
The normalized model and client UI will use precise executor-oriented terminology.

### Immediate Rendering Versus Efficiency

Per-event rendering would feel live but repeatedly processes unchanged history. Rendering
at bounded lifecycle points and incrementally updating the active commit is preferred.

### Token Detail Versus Parser Stability

Detailed Claude token categories depend on a potentially changing transcript format.
The parser will be isolated and fail visibly; file observability remains independent.

### One Large Change Versus Sequential Delivery

The work will be split so schema/capture, graph/UI, token accounting, and client
hardening can each be verified independently. A single large dashboard rewrite would
make provenance regressions difficult to locate.

## Rejected Alternatives

- Treating the domain owner as the executor for Claude-direct commits.
- Creating a fake delegated-agent self-report for direct execution.
- Using commit-spec files as evidence that a file was actually changed.
- Treating Git changes as evidence that Claude read a file.
- Estimating tokens from tool calls, time, diff size, or message length.
- Invoking an agent to summarize every commit during dashboard generation.
- Building overlays only from context packages.
- Displaying missing values as zero.
- Combining all measurements into an unexplained efficiency score.
- Reprocessing every historical artifact after every tool event.

## Implementation Sequence

### Phase 1: Canonical Schema And Capture

- Add the normalized commit evidence model.
- Start Claude-direct capture before implementation.
- Persist owner, executor, execution mode, file activity, and provenance.
- Add fail-closed checks for current-run telemetry completeness.
- Preserve backward compatibility for existing records.

### Phase 2: Graph And Measurement Rendering

- Build overlays from canonical records.
- Show every direct and delegated commit.
- Add planned/read/written/committed/change-type visual roles.
- Separate owner and executor labels.
- Replace blank or ambiguous cells with sourced states.

### Phase 3: Deterministic Token Accounting

- Add the versioned session-usage adapter.
- Reconcile Claude, agent, review, and repair usage without double counting.
- Add token budgets, cache categories, ratios, and capture completeness.
- Add deterministic rate-limit budget warnings.

### Phase 4: Backfill And Client Hardening

- Backfill only recoverable historical facts.
- Add reconciliation and release-blocking validation.
- Test browser behavior, accessibility, responsiveness, malformed data, and performance.
- Produce deterministic direct and delegated demonstration records.
- Publish client acceptance evidence.

## Required Tests

- Canonical schema validation and migration from current records.
- Owner/executor separation for Claude-direct and delegated commits.
- Git reconciliation for added, modified, renamed, deleted, and type-changed files.
- Direct overlay without a context package.
- Delegated overlay with package, agent activity, and Claude review activity.
- New graph nodes for files absent from the cached dependency graph.
- Missing telemetry displayed as unavailable, never zero.
- Token reconciliation without subagent double counting.
- Unknown transcript version produces an explicit partial state.
- Dashboard generation performs no model or agent invocation.
- Repeated generation from unchanged artifacts produces identical normalized data.
- Incremental rendering does not rescan unaffected history.

## Client Acceptance Invariants

Delivery is blocked unless all applicable current records satisfy:

```text
dashboard committed files == Git committed files
dashboard owner == approved specification owner
dashboard executor == actual executor
missing measurement != zero
every metric has provenance
every commit is navigable in the graph
token totals contain no duplicated invocation usage
dashboard collection and rendering make zero model calls
```

## Success Definition

The completed dashboard allows a client to select any commit and answer, from pure
recorded evidence:

1. What was planned?
2. Who owned the domain?
3. Who executed the work?
4. Which files were read, written, and committed?
5. What changed in the codebase graph?
6. How many tools and tokens were used?
7. How much of the declared budget was consumed?
8. Which values were measured, reconstructed, unavailable, or not applicable?
9. Did reconciliation confirm that the dashboard agrees with Git and telemetry?

No answer may depend on invented data or an implicit model judgment.
