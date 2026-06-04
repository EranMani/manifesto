# commit-protocol.md — Manifesto
> The canonical build sequence. Every commit planned before any code is written.
> Each commit is atomic — one concern, one owner, one clear test gate.
> No commit is made without Eran's approval. No two commits are combined.
> Status is maintained automatically by post_commit_next_step.py.

---

## Commit Index

| # | Name | Assignee | Status |
|---|---|---|---|
| 01 | project-scaffold | adam | pending |
| 02 | python-skeleton | rex | pending |
| 03 | frontend-scaffold | aria | pending |
| 04 | config-and-security | rex | pending |
| 05 | database-session | rex | pending |
| 06 | sqlalchemy-models | rex | pending |
| 07 | alembic-migration | rex | pending |
| 08 | seed-script | rex | pending |
| 09 | auth-dependencies | rex | pending |
| 10 | auth-route | rex | pending |
| 11 | admin-routes | rex | pending |
| 12 | vendor-routes | rex | pending |
| 13 | shipment-routes | rex | pending |
| 14 | product-routes | rex | pending |
| 15 | stub-routes | rex | pending |
| 16 | llm-service-stub | rex | pending |
| 17 | auth-store-and-client | aria | pending |
| 18 | protected-route | aria | pending |
| 19 | placeholder-pages | aria | pending |
| 20 | login-page | aria | pending |
| 21 | integration-smoke | adam | pending |

---

## Parallel Groups

```
Wave A: 02 ∥ 03  — python-skeleton (Rex) and frontend-scaffold (Aria) touch zero shared files
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
