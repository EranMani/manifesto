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
| 31 | telemetry-reconciliation | adam | ✅ done · 2026-06-12 |
| 32 | telemetry-dashboard-ledger | adam | ✅ done · 2026-06-12 |
| 33 | upload-duplicate-status | rex | ✅ done · 2026-06-13 |
| 33A | verify-constraints-ref-fix | claude | ✅ done · 2026-06-13 |
| 33B | finalize-commit-pipeline | claude | ✅ done · 2026-06-13 |
| 34 | database-test-container-command | adam | ✅ done · 2026-06-13 |
| 35 | policy-storage-db-url | rex | ✅ done · 2026-06-13 |
| 36 | ingestion-pgvector-write-integration | nova | ✅ done · 2026-06-13 |
| 37 | ingestion-status-transaction-integration | nova | ✅ done · 2026-06-13 |
| 38 | policy-query-embedding | nova | ✅ done · 2026-06-13 |
| 38A | orchestrator-telemetry-marker-gate | claude | ✅ done · 2026-06-13 |
| 39 | policy-vector-candidates | nova | ✅ done · 2026-06-14 |
| 40 | product-delivery-replan | claude | ✅ done · 2026-06-14 |
| 41 | purchase-order-storage | rex | ✅ done · 2026-06-14 |
| 42 | shipment-lifecycle-fields | rex | ✅ done · 2026-06-14 |
| 42A | purchase-order-migration-downgrade-fix | rex | ✅ done · 2026-06-14 |
| 43 | shipment-event-storage | rex | ✅ done · 2026-06-14 |
| 43A | shipment-lifecycle-migration-downgrade-fix | rex | ✅ done · 2026-06-14 |
| 44 | procurement-foundation-seed | rex | ✅ done · 2026-06-14 |
| 45 | shipment-scenario-seed | rex | ✅ done · 2026-06-14 |
| 46 | bundled-policy-seed | rex | ✅ done · 2026-06-14 |
| 47 | shipment-identifier-evidence | nova | ✅ done · 2026-06-14 |
| 47B | telemetry-lifecycle-overwrite-fix | claude | ✅ done · 2026-06-14 |
| 47C | telemetry-finalize-idempotency | claude | ✅ done · 2026-06-14 |
| 48 | procurement-relationship-evidence | nova | ✅ done · 2026-06-14 |
| 49 | shipment-timeline-evidence | nova | ✅ done · 2026-06-15 |
| 50 | logistics-graph-evidence | nova | ✅ done · 2026-06-15 |
| 51 | minimal-policy-evidence | nova | ✅ done · 2026-06-15 |
| 52 | assistant-intent-routing | nova | ✅ done · 2026-06-15 |
| 52A | claude-budget-and-cache-reduction | claude | ✅ done · retrospective · 796ef48 · 2026-06-15 |
| 53A | budget-override-closeout-fix | claude | ✅ done · e4f263c · 2026-06-15 |
| 53 | grounded-logistics-answer | nova | ✅ done · f73c22d · 2026-06-15 |
| 54A | powershell-budget-closeout-fix | claude | ✅ done · d25de0a · 2026-06-16 |
| 54 | grounded-policy-answer | nova | ✅ done · 7b269b2 · 2026-06-16 |
| 54B | rag-logistics-vendor-lookup-fix | rex | ✅ done · 94452d1 · 2026-06-16 |
| 55 | assistant-role-authorization | rex | ✅ done · 2026-06-16 |
| 56 | unified-assistant-api | rex | ✅ done · 4853404 · 2026-06-17 |
| 57 | assistant-client-session-state | aria | done |
| 58 | focused-evidence-graph | aria | ✅ done · 2026-06-17 |
| 59 | unified-assistant-interface | aria | ✅ done · 2026-06-17 |
| 60 | assistant-evidence-integration | aria | ✅ done · 2026-06-17 |
| 61 | assistant-golden-evaluation | nova | ✅ done · 2026-06-17 |
| 62 | assembled-client-demo | adam | ✅ done · 2026-06-17 |
| 63 | logistics-browse-intent | nova | ✅ done · 2026-06-17 |
| 64 | list-shipments-service | rex | ✅ done · 2026-06-17 |
| 65 | browse-answer-generation | nova | ✅ done · 2026-06-17 |
| 66 | graph-node-status-metadata | rex | ✅ done · 2026-06-17 |
| 66A | direct-brief-scope-exclusion | claude | ✅ done · 2026-06-17 |
| 67 | evidence-graph-visual-overhaul | aria | ✅ done · 2026-06-17 |
| 68 | policy-term-expansion | nova | ✅ done · 2026-06-18 |
| 69 | assistant-error-resilience | rex | ✅ done · 2026-06-18 |
| 69A | browse-markdown-formatting | nova | done |
| 70 | assistant-markdown-rendering | aria | ✅ done · 2026-06-18 |
| 71 | evidence-graph-timeline-layout | aria | ✅ done · 2026-06-18 |
| 72 | fix-policy-citation-uuid-types | rex | pending |
| 73 | fix-citation-frontend-uuid-types | aria | pending |

---

## Phase 3: Assistant Hardening (planned 2026-06-17)

C63-C65 address the first issue found in post-demo testing: general logistics
queries without a specific tracking code (e.g., "find all shipments", "show delayed
shipments") fail instantly instead of querying the database. The fix decomposes into
intent classification (C63), DB query wiring (C64), and LLM-grounded generation (C65).

C66-C67 address the second issue: the evidence graph is unreadable. The frontend
used policy-document color mappings for logistics node types (all nodes render gray),
a broken layout algorithm that stacks all nodes in one column (linear appearance),
and a cramped 384px container. C66 enriches graph nodes with status metadata (Rex),
C67 overhauls the visual rendering with logistics-aware colors, hub-and-spoke layout,
green/orange/red status encoding, and a wider graph area (Aria).

| Range | Product result |
|---|---|
| C63 | Intent routing distinguishes browse vs. single-shipment lookup |
| C64 | Browse queries reach the DB and return deterministic shipment summaries |
| C65 | LLM-grounded multi-shipment answers with fallback and count disclosure |
| C66 | Graph nodes carry status and status-category metadata for color encoding |
| C66A | Auto-generated direct briefs excluded from actual_scope file count |
| C67 | Readable hub-and-spoke graph with green/orange/red status coloring |
| C68 | Policy-adjacent queries (leave, rules, HR, performance) route correctly |
| C69 | Embedding/LLM errors return graceful fallbacks; browse queries get LLM grounding |
| C70 | Assistant responses render as formatted markdown with tables |
| C71 | Evidence graph splits entity details from chronological event timeline |
| C72 | Policy citations use UUID string types matching database columns |
| C73 | Frontend citation types aligned with backend UUID contract |

### Execution plan

C63, C64, and C66 are Claude-direct: mechanical pattern extensions with fully specified
contracts and no specialist uncertainty. C65 delegates to Nova (prompt engineering for
multi-shipment LLM context). C67 delegates to Aria (ReactFlow layout algorithm and
frontend visualization). Domain owners are preserved in the spec for file-access
validation; the `--direct` preflight flag selects Claude-direct execution at runtime.

---

## Fast-Delivery Product Replan (approved 2026-06-14)

C40 resets the active roadmap around the procurement-logistics demonstration while
preserving a minimal policy-document assistant. C41-C62 are specified in advance and
validated as one dependency graph before implementation begins.

**C40 review exception:** Eran explicitly waived the scheduled Viktor review for C40
only because it changes planning and project-state documents without runtime behavior.
The normal five-commit review cadence resumes at C45.

| Range | Product result |
|---|---|
| C41-C46 | Stable procurement scenarios and query-ready policy documents |
| C47-C50 | Traceable logistics facts, timelines, relationships, and graph evidence |
| C51-C56 | One role-aware backend assistant for logistics and policy questions |
| C57-C60 | Browser assistant with session chat, citations, and focused graph paths |
| C61-C62 | Golden-question verification and a clean client-demo rehearsal |

Deferred until demonstrations justify them: advanced policy rank fusion, durable
conversation history, SSE streaming and cancellation, provider selection, extensive
runtime metrics, and full-network graph exploration.

The reusable planning method and Manifesto worked example live in
`commit-specs/PRODUCT_DELIVERY_PLANNING.md`.

## Workflow Redesign And Phase 2 Recovery (historical, superseded 2026-06-14)

C29 installed enforcement. C29A builds the deterministic readiness scoring engine, C29B
wires it into `prepare_agent_delegation.py` as a hard gate before delegation, and C29C
exposes its report in the dashboard. C30-C76 apply the approved decomposition guide
without forcing the remaining work into an artificial endpoint.

C33A and C33B are an exceptional insertion (Rule 10 letter-suffix convention, no
renumbering of C34-C76) closing two determinism gaps found while finishing C33: C33A
fixes `verify_constraints.py`'s ref resolution so a re-run after a later commit lands
diffs the correct primary commit, and C33B adds `hooks/finalize_commit.py` plus a
fail-closed `pre_commit_check.py` gate so the verify -> dashboard -> notify-flag
sequence runs deterministically before any primary commit can land.

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
| C46 | Product | Inspect stable mock procurement data and query-ready policy documents |
| C50 | Product | Verify shipment facts, timelines, relationships, and graph paths |
| C56 | Product | Ask logistics and policy questions through one authenticated API |
| C60 | Application | Use answers, citations, focused graphs, and node details in the browser |
| C62 | Application | Rehearse the complete client demonstration from a clean environment |

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

Full specifications for each pending commit live in `commit-specs/`.
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
