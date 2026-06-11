# Commit 64 - `conversation-history-api` - Rex

**Phase:** Backend Policy Chat
**Owner:** rex
**Depends on:** C63
**Estimated diff lines:** 255
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Return owner-scoped paginated messages with citation snapshots.

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
  - backend/app/schemas/conversation.py
  - backend/app/api/v1/chat.py
  - backend/tests/api/test_conversations.py
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/schemas/conversation.py` | edit | Define message history contract |
| `backend/app/api/v1/chat.py` | edit | Implement history endpoint |
| `backend/tests/api/test_conversations.py` | edit | Prove history and citation snapshots |

---

## Contract

Return owner-scoped paginated messages with citation snapshots.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database and all prior migrations are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/api/test_conversations.py -k conversation_history -q
```

---

## Focused Tests

- Message order and pagination are stable.
- Citation snapshots survive reload without internal scores.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** The durable policy-chat backend is ready for API testing.
**How to test:** Run `docker compose run --rm backend uv run pytest tests/api/test_chat_policy.py tests/api/test_conversations.py -q`.
**Expected result:** Persistence, retry, concurrency rejection, conversation listing, history, and citations pass.
**Still incomplete:** The visible frontend experience begins in C65.

---

## Not In This Commit

- Frontend implementation starts C65.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
