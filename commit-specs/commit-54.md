# Commit 54 - `policy-chat-request-schema` - Rex

**Phase:** Backend Policy Chat
**Owner:** rex
**Depends on:** C53
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Freeze validated policy-chat requests and typed SSE event schemas.

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
  - backend/app/schemas/chat.py
initial_context:
  - backend/app/schemas/chat.py
  - backend/tests/api/test_chat_policy.py
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/schemas/chat.py` | new | Define request and event models |
| `backend/tests/api/test_chat_policy.py` | new | Prove schema validation |

---

## Contract

Freeze validated policy-chat requests and typed SSE event schemas.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database and all prior migrations are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/api/test_chat_policy.py -k schema -q
```

---

## Focused Tests

- Provider and message validation is exact.
- Every event payload has a stable type.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C56.

---

## Not In This Commit

- No route streaming until C55.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
