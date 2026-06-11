# Commit 56 - `policy-chat-stream-errors` - Rex

**Phase:** Backend Policy Chat
**Owner:** rex
**Depends on:** C55
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Map pre-stream and mid-stream failures to stable public SSE behavior.

---

## Semantic Fit Review

- **Atomic outcome:** One backend contract or persistence behavior is introduced.
- **Failure boundary:** Later route, persistence, or read behavior remains isolated.
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
  - backend/app/api/v1/chat.py
initial_context:
  - backend/app/api/v1/chat.py
  - backend/tests/api/test_chat_policy.py
  - backend/app/services/rag_policy.py
  - backend/app/schemas/chat.py
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/api/v1/chat.py` | edit | Normalize stream failures and disconnects |
| `backend/tests/api/test_chat_policy.py` | edit | Prove error and disconnect contracts |

---

## Contract

Map pre-stream and mid-stream failures to stable public SSE behavior.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database and all prior migrations are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/api/test_chat_policy.py -k stream_errors -q
```

---

## Focused Tests

- Pre-stream failures use HTTP errors.
- Mid-stream failures emit one safe terminal event.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** The authenticated policy SSE API is ready for direct testing.
**How to test:** Start the stack with `docker compose up -d`, authenticate, then POST to `/api/v1/chat/policy` and inspect named SSE events.
**Expected result:** The response streams typed events incrementally and exposes stable public errors.
**Still incomplete:** Durable conversation persistence begins in C57.

---

## Not In This Commit

- No durable message state until C57.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
