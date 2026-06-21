# Commit 96 - `badge-selection-engine` - Rex

**Phase:** Phase 4 (Action Badges)
**Owner:** rex
**Depends on:** C95
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

The assistant query response includes contextual action badges (2-3 per answer) selected by a deterministic engine that maps shipment status, latest event type, and user role to relevant next-action suggestions.

---

## Semantic Fit Review

- **Atomic outcome:** After this commit, every logistics assistant response includes an `action_badges` array in the JSON payload. The badge selection is purely deterministic (no LLM calls) and testable with unit assertions on known inputs.
- **Failure boundary:** If badge selection fails or produces an empty list, the response still succeeds with `action_badges: []`. The assistant answer itself is unaffected.
- **Budget rationale:** Three files (1 new service, 2 edits to schema/route), all in Rex's backend domain. The badge engine is a pure function with a static mapping dict — no DB queries, no new models, no migrations.

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
  - backend/app/services/badge_engine.py
  - backend/app/schemas/assistant.py

initial_context:
  - commit-specs/commit-96.md
  - backend/app/services/badge_engine.py
  - backend/app/schemas/assistant.py
  - backend/app/api/v1/assistant.py
  - docs/product-concepts/assistant-action-badges.md

forbidden:
  - frontend/
  - hooks/
  - backend/app/services/rag_logistics.py
  - backend/app/services/rag_policy.py
  - backend/app/services/llm.py
  - backend/app/services/ingestion.py
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/badge_engine.py` | add | Deterministic badge selection engine: status+event+role → badges |
| `backend/app/schemas/assistant.py` | edit | Add ActionBadgeSchema and action_badges field to AssistantQueryResponse |
| `backend/app/api/v1/assistant.py` | edit | Call badge engine in _to_response, pass user role and graph data |

---

## Contract

### Badge Engine (`select_badges`)

**Inputs:**
- `status: str` — shipment status (one of: pending, in_transit, delayed, delivered, partial, damaged, cancelled, returned, lost)
- `latest_event_type: str | None` — most recent event type from timeline (e.g., customs_hold, delay_reported)
- `role: str` — user role (admin, manager, employee)

**Outputs:**
- `list[ActionBadge]` — 0-3 badge objects, each with:
  - `label: str` — display text for the badge chip (e.g., "Ask vendor for explanation")
  - `prompt: str` — the message to send to the assistant when clicked (e.g., "Ask the vendor for an explanation of the delay on this shipment")

**Rules:**
- Maximum 3 badges per call
- Employee role returns employee-specific badges (Read full policy, Ask a follow-up, Talk to my manager, Report an issue) — max 3 selected
- Admin/manager roles return operational badges based on status mapping from the product concept
- If `latest_event_type` is `customs_hold`, override the status-based selection with customs-specific badges
- If status is `delivered`, return empty list (no actions needed)
- Unknown/unrecognized status returns empty list

### Schema Addition

`ActionBadgeSchema`:
```python
class ActionBadgeSchema(BaseModel):
    label: str
    prompt: str
```

`AssistantQueryResponse.action_badges: list[ActionBadgeSchema] = []`

### Route Integration

In `_to_response()` or the route handler:
1. Extract shipment status from graph nodes (find node with `type == "shipment"`, read `status`)
2. Extract latest event type from graph nodes (find last node with `type == "event"`, read `label`)
3. Call `select_badges(status, latest_event_type, role)`
4. Include result in response

The route handler passes `current_user.role` to `_to_response` (signature change).

---

## Environment Prerequisites

- Backend running (Docker or local)
- No new dependencies, migrations, or services required

---

## Verification Command

```powershell
docker compose run --rm backend uv run python -c "from app.services.badge_engine import select_badges; badges = select_badges('delayed', 'delay_reported', 'manager'); assert badges; assert len(badges) in (1, 2, 3); assert all(hasattr(b, 'label') and hasattr(b, 'prompt') for b in badges); print(f'PASS: {len(badges)} badges for delayed shipment')"
```

---

## Focused Tests

- **Happy path:** Delayed shipment with delay_reported event + manager role → returns 3 badges with expected labels (Ask vendor for explanation, Extend delivery estimate, Escalate to manager)
- **Employee override:** Any shipment status + employee role → returns employee-specific badges (Read full policy, Ask a follow-up, Talk to my manager)
- **Customs hold override:** In-transit shipment with customs_hold event → returns customs-specific badges regardless of status
- **Delivered/empty:** Delivered shipment → returns empty list
- **No graph (policy intent):** When intent is "policy" and no graph exists → returns employee badges for employees, empty for managers

---

## Done When

- [ ] `badge_engine.py` exists with `select_badges()` returning correct badges for all 9 statuses
- [ ] `AssistantQueryResponse` includes `action_badges` field
- [ ] Route handler calls badge engine and populates the field
- [ ] Verification command passes in Docker

---

## Developer Test Checkpoint

- **Next milestone:** C97 (badge-chips-frontend) — full action badges Phase 1
  testable in the browser.

---

## Not In This Commit

- Frontend badge rendering (C97)
- Badge click confirmation flow (Phase 2, future)
- Badge action execution handlers (Phase 3, future)
- Proactive badge suggestions without user query (future)

---

## Return Contract

The implementor's final message must begin with this concise human summary:

```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```

After the human summary, include the structured telemetry JSON required by the
generated delegation brief. If the commit cannot finish within its budget, also
include the `SPLIT_REQUIRED` report.
