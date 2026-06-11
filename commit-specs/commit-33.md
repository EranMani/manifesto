# Commit 33 - `upload-duplicate-status` - Rex

**Phase:** Product And Test Recovery
**Owner:** rex
**Depends on:** C29C
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Return HTTP 201 for a new document and HTTP 200 for an identical ready document.

---

## Semantic Fit Review

- **Atomic outcome:** One route contract distinguishes creation from idempotent reuse.
- **Failure boundary:** Ingestion database integration remains C36-C37.
- **Budget rationale:** 2 exact changed file(s), 4 initial context file(s), and one focused verification command fit one bounded invocation.

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
```

---

## Context

```yaml
primary_files:
  - backend/app/api/v1/documents.py
initial_context:
  - commit-specs/commit-33.md
  - backend/app/api/v1/documents.py
  - backend/tests/api/test_documents.py
  - commit-specs/commit-28.md
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/api/v1/documents.py` | edit | Return branch-specific status codes |
| `backend/tests/api/test_documents.py` | edit | Regress new and duplicate branches |

---

## Contract

Return HTTP 201 for a new document and HTTP 200 for an identical ready document.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database is healthy and migrations are applied.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/api/test_documents.py -q
```

---

## Focused Tests

- New upload returns 201.
- Duplicate ready upload returns 200 without ingestion or a new row.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C37.

---

## Not In This Commit

- No ingestion service changes.
- No response-shape redesign.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
