# Commit 60 - `chat-stream-persistence` - Rex

**Phase:** Backend Policy Chat
**Owner:** rex
**Depends on:** C59
**Estimated diff lines:** 255
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Persist assistant completion, cancellation, and failure around the SSE lifecycle.

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
  - backend/app/services/conversation.py
  - backend/app/api/v1/chat.py
initial_context:
  - commit-specs/commit-60.md
  - backend/app/services/conversation.py
  - backend/app/api/v1/chat.py
  - backend/tests/api/test_chat_persistence.py
  - commit-specs/commit-59.md
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/conversation.py` | edit | Implement assistant terminal writes |
| `backend/app/api/v1/chat.py` | edit | Call persistence around streaming |
| `backend/tests/api/test_chat_persistence.py` | edit | Prove all terminal states |

---

## Contract

Persist assistant completion, cancellation, and failure around the SSE lifecycle.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database and all prior migrations are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/api/test_chat_persistence.py -k stream_persistence -q
```

---

## Focused Tests

- Completed content and citations persist.
- Cancelled or failed partial output is never completed.

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

- Idempotent replay is C61.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
