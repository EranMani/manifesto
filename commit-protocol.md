# commit-protocol.md — Manifesto
> The canonical build sequence. Every commit planned before any code is written.
> Each commit is atomic — one concern, one owner, one clear test gate.
> No commit is made without Eran's approval. No two commits are combined.
> Status is maintained automatically by post_commit_next_step.py.

---

## Commit Index

| # | Name | Assignee | Status |
|---|---|---|---|
| 01 | project-scaffold | adam | done |
| 02 | python-skeleton | rex | ✅ done · 2026-06-04 |
| 03 | frontend-scaffold | aria | ✅ done · 2026-06-04 |
| 04 | config-and-security | rex | ✅ done · 2026-06-04 |
| 04b | config-security-hardening | rex | ✅ done · 2026-06-05 |
| 05 | database-session | rex | ✅ done · 2026-06-05 |
| 06 | sqlalchemy-models | rex | ✅ done · 2026-06-05 |
| 07 | alembic-migration | rex | ✅ done · 2026-06-05 |
| 08 | seed-script | rex | ✅ done · 2026-06-05 |
| 09 | auth-dependencies | rex | ✅ done · 2026-06-05 |
| 10 | auth-route | rex | ✅ done · 2026-06-05 |
| 11 | admin-routes | rex | ✅ done · 2026-06-05 |
| 12 | vendor-routes | rex | ✅ done · 2026-06-05 |
| 13 | shipment-routes | rex | ✅ done · 2026-06-05 |
| 14 | product-routes | rex | ✅ done · 2026-06-05 |
| 15 | stub-routes | rex | ✅ done · 2026-06-05 |
| 15a | fix-admin-update | rex | ✅ done · 2026-06-05 |
| 15b | fix-vendor-update | rex | ✅ done · 2026-06-06 |
| 15c | fix-product-update | rex | ✅ done · 2026-06-06 |
| 16 | llm-service-stub | rex | ✅ done · 2026-06-06 |
| 17 | auth-store-and-client | aria | ✅ done · 2026-06-06 |
| 18 | protected-route | aria | ✅ done · 2026-06-06 |
| 19 | placeholder-pages | aria | ✅ done · 2026-06-06 |
| 20 | login-page | aria | ✅ done · 2026-06-07 |
| 21 | integration-smoke | adam | ✅ done · 2026-06-07 |
| 22 | fix-login-request-format | aria | ✅ done · 2026-06-07 |
| 23 | pgvector-migration | rex | ✅ done · pre-existing (0001_initial.py) · 2026-06-08 |
| 24 | llm-runtime-config | rex | ✅ done · 2026-06-09 |
| 25 | llm-service-impl | nova | ✅ done · 2026-06-09 |
| 26 | rag-storage-hardening | rex | ✅ done · 2026-06-10 |
| 27 | document-ingestion | nova | ✅ done · 2026-06-10 |
| 28 | document-upload-routes | rex | ✅ done · 2026-06-10 |
| 29 | agent-budget-circuit-breaker | claude | ✅ done · 2026-06-10 |
| 29A | preflight-score-engine | adam | ✅ done · 2026-06-11 |
| 29B | preflight-delegation-gate | adam | ✅ done · 2026-06-11 |
| 29C | preflight-dashboard-details | adam | ✅ done · 2026-06-12 |
| 30 | invocation-record-storage | adam | ✅ done · 2026-06-12 |
| 31 | telemetry-reconciliation | adam | pending |
| 32 | telemetry-dashboard-ledger | adam | pending |
| 33 | upload-duplicate-status | rex | pending |
| 34 | database-test-container-command | adam | pending |
| 35 | policy-storage-db-url | rex | pending |
| 36 | ingestion-pgvector-write-integration | nova | pending |
| 37 | ingestion-status-transaction-integration | nova | pending |
| 38 | policy-query-embedding | nova | pending |
| 39 | policy-vector-candidates | nova | pending |
| 40 | policy-lexical-candidates | nova | pending |
| 41 | policy-rank-fusion | nova | pending |
| 42 | policy-result-diversification | nova | pending |
| 43 | policy-evidence-threshold | nova | pending |
| 44 | policy-context-budget | nova | pending |
| 45 | policy-source-labels | nova | pending |
| 46 | policy-grounded-prompt | nova | pending |
| 47 | policy-stream-events | nova | pending |
| 48 | policy-stream-cancellation | nova | pending |
| 49 | policy-citation-validation | nova | pending |
| 50 | policy-evaluation-dataset | nova | pending |
| 51 | policy-retrieval-metrics | nova | pending |
| 52 | policy-answer-quality-metrics | nova | pending |
| 53 | policy-runtime-baselines | nova | pending |
| 54 | policy-chat-request-schema | rex | pending |
| 55 | policy-chat-sse-route | rex | pending |
| 56 | policy-chat-stream-errors | rex | pending |
| 57 | message-stream-state-schema | rex | pending |
| 58 | message-citation-schema | rex | pending |
| 59 | conversation-write-service | rex | pending |
| 60 | chat-stream-persistence | rex | pending |
| 61 | chat-idempotent-retry | rex | pending |
| 62 | conversation-send-concurrency | rex | pending |
| 63 | conversation-list-api | rex | pending |
| 64 | conversation-history-api | rex | pending |
| 65 | frontend-test-baseline | aria | pending |
| 66 | chat-sse-client | aria | pending |
| 67 | policy-chat-state | aria | pending |
| 68 | stream-message-rendering | aria | pending |
| 69 | message-input-cancel | aria | pending |
| 70 | provider-selection-ui | aria | pending |
| 71 | conversation-api-client | aria | pending |
| 72 | conversation-sidebar-list | aria | pending |
| 73 | conversation-history-navigation | aria | pending |
| 74 | citations-ui | aria | pending |
| 75 | policy-chat-ui-integration | aria | pending |
| 76 | assembled-policy-chat-smoke | adam | pending |

---

## Workflow Redesign And Phase 2 Recovery (revised 2026-06-10)

C29 installed enforcement. C29A builds the deterministic readiness scoring engine, C29B
wires it into `prepare_agent_delegation.py` as a hard gate before delegation, and C29C
exposes its report in the dashboard. C30-C76 apply the approved decomposition guide
without forcing the remaining work into an artificial endpoint.

| Range | Phase | Primary result |
|---|---|---|
| C29A | Workflow preflight | Build, score, and persist the deterministic readiness report |
| C29B | Workflow preflight | Block delegation on a non-proceeding preflight result |
| C29C | Preflight visibility | Show confidence and expandable Python diagnostics for each commit |
| C30-C32 | Workflow trust | Separate invocation storage, reconciliation, and dashboard presentation |
| C33-C37 | Product/test recovery | Repair upload status and establish container, storage, and ingestion database verification |
| C38-C53 | Policy RAG | Build query, retrieval, ranking, grounding, streaming, citations, and evaluation as independent behaviors |
| C54-C64 | Backend chat | Freeze request/stream contracts, then add persistence, idempotency, concurrency, and history APIs |
| C65-C75 | Frontend chat | Establish tests, then add transport, state, rendering, controls, history, citations, and integration coverage |
| C76 | Assembled verification | Prove the complete policy-chat path through the running stack |

Every row is a planning candidate only until its `commit-specs/commit-NN.md` file passes
`hooks/validate_commit_spec.py`.

### Planning Envelope

Each pending commit targets:

- One observable behavior and one owner.
- No more than two primary files.
- No more than four changed files.
- 200-280 estimated changed lines where practical; 350 is the hard ceiling.
- Three to five initial context files; six is the hard ceiling.
- One focused verification command.
- One normal implementor invocation, 18 tool calls, and 45,000 implementor tokens.

The sequence may grow again if exact spec drafting reveals a candidate that cannot keep
this margin.

`hooks/validate_commit_spec.py` already enforces these numeric limits against
`LOCKED_BUDGET` (`max_primary_files`, `max_context_files`, `max_changed_files`,
`max_estimated_diff_lines`, and the execution budget's tool-call/token caps) when run
per rule 11. A spec that exceeds this envelope fails validation before any delegation
package or Commit Preview is produced — no separate envelope check is needed.

### Budget Profiles

| Profile | tool calls | implementor tokens | total tokens | expansions | When |
|---|---|---|---|---|---|
| Default | 18 | 45,000 | 60,000 | 2 | All commits, unless a greenfield exception is authorized |
| Greenfield-module | 28 | 55,000 | 70,000 | 2 | Per-commit `bootstrap_exception` override, authorized by Eran, for a commit creating a wholly new module plus its full test suite from scratch with no existing implementation to read or edit |

The greenfield-module profile is opt-in via the spec's `bootstrap_exception` block.
`validate_commit_spec.py` validates the block's fields against the greenfield ceilings
and returns the merged effective budget; `prepare_agent_delegation.py` propagates that
effective budget into `hooks/tool_cap.json` automatically, with no manual editing. It
does not change the default profile for ordinary commits. First applied to C29A
(2026-06-11) after a second consecutive zero-code `SPLIT_REQUIRED`.

### Developer Test Milestones

Small commits remain independently verified, but Claude announces a developer milestone
only when a coherent capability is ready to test.

| After | Type | Eran can test |
|---|---|---|
| C32 | Technical | Open the constraint dashboard and inspect separate invocation records, totals, and contradictions |
| C37 | Technical | Run document upload and ingestion against the real database, including success and rollback paths |
| C49 | Technical | Exercise the complete policy RAG service contract through focused service tests |
| C56 | Technical | Call the authenticated policy SSE endpoint and inspect incremental events and public errors |
| C64 | Technical | Test durable conversations, retries, concurrency rejection, history, and citations through backend APIs |
| C70 | Application | Open Policy Chat and visually test provider selection, sending, streaming text, stop, and safe retry |
| C73 | Application | Open Policy Chat and test conversation sidebar navigation, reload, and browser back/forward |
| C74 | Application | Ask a policy question and visually inspect live and historical citation rendering |
| C76 | Application | Run the complete upload -> ask -> stream -> reload -> citations workflow in the assembled application |

After a milestone commit passes its gates, Claude tells Eran:

```text
DEVELOPER TEST MILESTONE READY
Ready now: [capability]
How to test: [exact startup command, URL or API call, and short steps]
Expected result: [observable result]
Still incomplete: [later commits not included]
```

A milestone is based on feature readiness, not elapsed commit count. Claude must not say
"the feature is ready" merely because five commits passed.

---

## Parallel Groups

```
Wave A: 02 ∥ 03   — python-skeleton (Rex) and frontend-scaffold (Aria) touch zero shared files
Wave A2: 25 ∥ 26  — provider adapters (Nova) and additive storage migration (Rex) share
                     only the frozen embedding profile from C24
No C30-C76 parallel group is pre-approved. Parallel execution may be proposed only after
the exact specs validate, ownership is disjoint, and neither commit consumes the other's
uncommitted contract.
```

---

## Commit Specs

Full specifications for each commit live in `commit-specs/`.
Load `commit-specs/commit-XX.md` (active commit only) when executing a step.

---

## Protocol Rules

1. Commits are made in the order listed. No skipping.
2. Each commit requires Eran's approval before it is made.
3. The assignee does the work. Cross-domain touches are flagged as handoffs before the commit.
4. Testing gate must pass before approval is surfaced.
5. If a commit reveals a prior commit needs changing — stop. Surface to Eran first.
6. `DECISIONS.md` and `ARCHITECTURE.md` are updated by Claude before every approval prompt when applicable.
7. Scope overflow is logged immediately — never silently absorbed.
8. Viktor reviews every 5th numbered commit (C05, C10, C15, and continuing at C30,
   C35, C40, and so on). Sage reviews any commit touching auth, secrets, user input, or
   external API calls.
9. No gate-fix passes. A blocking finding becomes its own next commit.
10. New pending work uses the next integer and the pending range is renumbered when needed.
    Letter suffixes (`24a`, `24b`) are reserved for exceptional fixes after later numbered
    commits already exist or are immutable; they are not used for ordinary planning.
11. Every pending specification must pass `hooks/validate_commit_spec.py` before a
    delegation package or Commit Preview is produced. After creating or renumbering the
    pending range, the full graph must also pass
    `python hooks/validate_commit_spec.py --all-pending --json`.
12. A budget failure is non-waivable. Remaining work becomes a new sequential commit.
13. An implementor may return `SPLIT_REQUIRED`; Claude drafts the replacement spec and
    Eran approves it before execution continues.
14. Passing structural validation does not prove semantic fit. If exact files, tests, or
    contracts exceed the planning envelope, split the commit and renumber the pending
    range before delegation.
15. When a commit closes a listed Developer Test Milestone, Claude surfaces the milestone
    notice after automated verification and before starting the next commit.
16. Before `prepare_agent_delegation.py` invokes an implementor, Claude runs the
    deterministic preflight gate. Delegation proceeds only when readiness is at least
    80 and no blocking violation exists. Detailed diagnostics remain on disk; Claude
    reads them only when the gate blocks or a warning requires developer attention.
17. C29A is the only full bootstrap exception, because the preflight script does not
    exist before its own implementation. Before invoking C29B, Claude manually runs
    `python hooks/preflight_commit.py --commit 29B --agent adam --json` and confirms
    `score >= 80` with zero `blocking_violations`; C29B does not proceed otherwise.
    Automatic preflight enforcement inside `prepare_agent_delegation.py` begins after
    C29B is committed, applying to C29C and every later implementor delegation.
    Dashboard rendering is observational and never overrides the Python gate result.
18. A passing preflight produces a compact approval card containing score/status,
    `Owner: Name (Domain)`, one-sentence goal, every planned file with its action, exact
    warning text, and whether a decision is required. Claude loads detailed diagnostics
    only for a blocked result, decision-required warning, changed scope, or split/repair.
19. Claude-direct execution is the default after approval. The card names the executor.
    Delegation requires a written justification based on unresolved specialist
    uncertainty, independent implementation needed for risk control, or a clearly
    bounded specialist unit whose expected value exceeds invocation overhead. Domain
    ownership alone is insufficient. Claude-direct commits include
    `Execution: Claude-direct` and are mechanically limited to the active spec's
    `Files To Modify Or Add` table.
