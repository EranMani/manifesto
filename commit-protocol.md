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
| 24 | llm-runtime-config | rex | pending |
| 25 | llm-service-impl | nova | pending |
| 26 | rag-storage-hardening | rex | pending |
| 27 | document-ingestion | nova | pending |
| 28 | document-upload-routes | rex | pending |
| 29 | rag-policy-pipeline | nova | pending |
| 30 | policy-chat-routes | rex | pending |
| 31 | conversation-persistence | rex | pending |
| 32 | policy-chat-ui | aria | pending |
| 33 | conversation-sidebar-ui | aria | pending |
| 34 | citations-ui | aria | pending |

---

## Phase 2 — Policy RAG (added via /replan, 2026-06-07)

Added per `manifesto-spec.md` §Phase 2. See `replan_history` in `project-state.json`
for the trigger record. Architecture review on 2026-06-08 expanded the sequence to
resolve runtime ownership and storage-contract blockers before implementation.

```
C23 → C24 → {C25 ∥ C26} → C27 → {C28 ∥ C29} → C30
    → {C31 ∥ C32} → C33 → C34
```

C28 cannot run in parallel with C27 because its route calls C27's ingestion contract.

---

## Parallel Groups

```
Wave A: 02 ∥ 03   — python-skeleton (Rex) and frontend-scaffold (Aria) touch zero shared files
Wave A2: 25 ∥ 26  — provider adapters (Nova) and additive storage migration (Rex) share
                     only the frozen embedding profile from C24
Wave B: 28 ∥ 29   — upload routes and retrieval pipeline both depend on C27's frozen
                     ingestion/storage contract, but do not touch each other's files
Wave C: 31 ∥ 32   — persistence and the initial chat UI both build against C30's
                     versioned SSE contract; C33 joins them
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
