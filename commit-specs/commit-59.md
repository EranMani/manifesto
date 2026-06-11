# Commit 59 - `conversation-write-service` - Rex

**Phase:** Backend Policy Chat
**Owner:** rex
**Depends on:** C58
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Create an owned policy conversation and persist its initial user message.

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
  - backend/app/services/conversation.py
initial_context:
  - commit-specs/commit-59.md
  - backend/app/services/conversation.py
  - backend/tests/api/test_chat_persistence.py
  - commit-specs/commit-58.md
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/conversation.py` | new | Implement owned conversation creation |
| `backend/tests/api/test_chat_persistence.py` | new | Prove ownership and first-message writes |

---

## Contract

Create an owned policy conversation and persist its initial user message.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database and all prior migrations are available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/api/test_chat_persistence.py -k conversation_write -q
```

---

## Focused Tests

- New conversation stores fixed provider and title.
- Cross-user conversation access is indistinguishable from missing.

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

- Assistant terminal persistence is C60.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
