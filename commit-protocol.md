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
| 30 | telemetry-per-invocation | claude | pending |
| 31 | document-upload-status-contract | rex | pending |
| 32 | database-test-baseline | rex | pending |
| 33 | ingestion-database-integration | nova | pending |
| 34 | policy-retrieval-candidates | nova | pending |
| 35 | policy-rank-fusion | nova | pending |
| 36 | policy-grounding-context | nova | pending |
| 37 | policy-stream-citations | nova | pending |
| 38 | policy-rag-evaluation | nova | pending |
| 39 | policy-chat-routes | rex | pending |
| 40 | conversation-persistence | rex | pending |
| 41 | policy-chat-ui | aria | pending |
| 42 | conversation-sidebar-ui | aria | pending |
| 43 | citations-ui | aria | pending |

---

## Workflow Redesign And Phase 2 Recovery (approved 2026-06-10)

Product work is frozen until C29 installs the commit-level circuit breaker. C30 restores
telemetry trust, C31-C33 restore product/test contracts, and C34-C38 split the former
RAG pipeline epic into bounded commits. Existing product work resumes at C39.

```
C29 → C30 → {C31 ∥ C32} → C33 → C34 → C35 → C36 → C37 → C38
    → C39 → {C40 ∥ C41} → C42 → C43
```

C31 may run after C29 without waiting for C30. Database and RAG work proceeds
sequentially from C32 because each step establishes the verification baseline for the
next.

---

## Parallel Groups

```
Wave A: 02 ∥ 03   — python-skeleton (Rex) and frontend-scaffold (Aria) touch zero shared files
Wave A2: 25 ∥ 26  — provider adapters (Nova) and additive storage migration (Rex) share
                     only the frozen embedding profile from C24
Wave B: 31 ∥ 32   — upload contract correction and database-test baseline touch separate
                     focused surfaces after the circuit breaker is active
Wave C: 40 ∥ 41   — persistence and the initial chat UI both build against C39's
                     versioned SSE contract; C42 joins them
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
8. Viktor reviews every 5th commit (C05, C10, C15, C20). Sage reviews any commit touching auth, secrets, or external API calls.
9. No gate-fix passes. A blocking finding becomes its own next commit.
10. New pending work uses the next integer and the pending range is renumbered when needed.
    Letter suffixes (`24a`, `24b`) are reserved for exceptional fixes after later numbered
    commits already exist or are immutable; they are not used for ordinary planning.
11. Every pending specification must pass `hooks/validate_commit_spec.py` before a
    delegation package or Commit Preview is produced.
12. A budget failure is non-waivable. Remaining work becomes a new sequential commit.
13. An implementor may return `SPLIT_REQUIRED`; Claude drafts the replacement spec and
    Eran approves it before execution continues.
