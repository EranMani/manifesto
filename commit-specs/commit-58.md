# Commit 58 - `message-citation-schema` - Rex

**Phase:** Backend Policy Chat
**Owner:** rex
**Depends on:** C57
**Estimated diff lines:** 255
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Persist ordered citation snapshots separately from messages.

---

## Semantic Fit Review

- **Atomic outcome:** One backend contract or persistence behavior is introduced.
- **Failure boundary:** Later route, persistence, or read behavior remains isolated.
- **Budget rationale:** 3 exact changed file(s), 5 initial context file(s), and one focused verification command fit one bounded invocation.

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
  - backend/alembic/versions/0004_message_citations.py
  - backend/app/models/message_citation.py
initial_context:
  - commit-specs/commit-58.md
  - backend/alembic/versions/0004_message_citations.py
  - backend/app/models/message_citation.py
  - backend/tests/models/test_message_citations.py
  - commit-specs/commit-57.md
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/alembic/versions/0004_message_citations.py` | new | Create citation table and indexes |
| `backend/app/models/message_citation.py` | new | Map citation snapshots |
| `backend/tests/models/test_message_citations.py` | new | Prove ordering, deletion, and downgrade |

---

## Contract

Persist ordered citation snapshots separately from messages.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database and all prior migrations are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/models/test_message_citations.py -k message_citations -q
```

---

## Focused Tests

- Ordered snapshots persist.
- Deleting a message cascades safely.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C64.

---

## Not In This Commit

- Conversation writes are C59.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
