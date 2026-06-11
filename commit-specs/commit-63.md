# Commit 63 - `conversation-list-api` - Rex

**Phase:** Backend Policy Chat
**Owner:** rex
**Depends on:** C62
**Estimated diff lines:** 255
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Return owner-scoped cursor-paginated policy conversations.

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
  - backend/app/schemas/conversation.py
  - backend/app/api/v1/chat.py
initial_context:
  - commit-specs/commit-63.md
  - backend/app/schemas/conversation.py
  - backend/app/api/v1/chat.py
  - backend/tests/api/test_conversations.py
  - commit-specs/commit-62.md
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/schemas/conversation.py` | new | Define conversation list contract |
| `backend/app/api/v1/chat.py` | edit | Implement list endpoint |
| `backend/tests/api/test_conversations.py` | new | Prove ownership and pagination |

---

## Contract

Return owner-scoped cursor-paginated policy conversations.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database and all prior migrations are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/api/test_conversations.py -k conversation_list -q
```

---

## Focused Tests

- Stable cursor ordering is preserved.
- Other users' conversations never appear.

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

- Message history is C64.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
