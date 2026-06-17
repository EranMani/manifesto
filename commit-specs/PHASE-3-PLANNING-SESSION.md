# Phase 3 Planning Session — 2026-06-17

## Trigger

Eran completed the Phase 2 client demo (C62) and began hands-on testing. Two issues
were identified from actual product usage, not from test suites or code review.

## Issue 1: General logistics queries fail without a tracking code

### Discovery

Eran typed "find all shipments" in the assistant and received:

> I couldn't find a shipment matching that query. Please include a specific tracking
> code (e.g. SHP-1001) and I'll look it up for you.

Every query without an explicit `SHP-####` tracking code produced this error — the
assistant was unusable for general logistics questions.

### Root cause analysis

Claude traced the full call chain before invoking any agents:

1. `classify_intent()` (`rag_logistics.py:639`) — defaults ambiguous queries (no
   tracking code, no policy terms) to `logistics` intent with empty `tracking_codes`
   and confidence 0.5.
2. `_primary_tracking_code()` (`assistant.py:106`) — returns `""` when the list is empty.
3. `generate_grounded_logistics_answer()` calls `lookup_procurement()` which calls
   `_load_shipment()` with `""`.
4. `_load_shipment()` (`rag_logistics.py:158`) raises `ShipmentNotFoundError("tracking
   code is blank")`.
5. The catch block (`assistant.py:68-74`) returns the generic error message.

The pipeline was **single-shipment-only by design**. No code path existed for queries
without a tracking code. Meanwhile, the REST API (`shipments.py`) already had a working
`GET /shipments` endpoint.

### Agent discussion (attempted)

Eran requested Nova and Rex be invoked to discuss the issue. Both invocations were
blocked by hooks:

- **Nova**: `tool_cap_start.py` returned `CIRCUIT BREAKER: commit is stopped:
  implementor_token_hard_stop`. The `tool_cap.json` was stale from C61, where Nova's
  invocation consumed 59,694 tokens against a 45,000 hard stop.
- **Rex**: `CIRCUIT BREAKER: prepared agent is nova, requested rex`. The tool cap state
  was prepared for Nova (C61's agent), so Rex couldn't start.

Since this was a discussion session (not implementation), Claude synthesized both
perspectives from the code already read:

**Nova's perspective (AI/RAG):**
- Intent classification needs a new `logistics_browse` category — the current 3-way
  `logistics|policy|mixed` doesn't distinguish "tell me about SHP-1001" from "show me
  all delayed shipments."
- The ambiguous default (confidence 0.5) should route to browse, not single-lookup.
- LLM prompt needs a multi-shipment variant; dumping all shipments would blow token
  limits — cap at 20.
- Deterministic fallback should be the default for list queries (higher hallucination
  risk with aggregation questions).

**Rex's perspective (backend/data):**
- Need `list_shipments_summary()` — lighter than `lookup_procurement()`, returns
  `ShipmentEvidence` without vendor/PO/product/timeline joins.
- Hard cap at 20 shipments. Status filter extracted from question text.
- `answer_question()` needs a new branch before the existing logistics path.
- `AssistantQueryResponse` schema works as-is for list results.

### Decomposition into commits

The fix was split into three commits following the planning envelope (max 2 primary
files, 4 changed files, 18 tool calls):

| Commit | Scope | Why separate |
|--------|-------|--------------|
| C63 | Intent routing only | Adds the new intent type and detection vocabulary. No DB queries, no generation. Isolates the classification change so it can be tested independently. |
| C64 | DB query + orchestrator wiring | Adds the SQL query and connects the new intent to `answer_question()`. Produces deterministic output only — no LLM call. |
| C65 | LLM-grounded generation | Adds prompt engineering for multi-shipment context. This is the commit with genuine specialist uncertainty (how to format 20 shipments for an LLM and avoid hallucination). |

### Validation failure and fix

C65 initially included changes to `assistant.py` and `tests/api/test_assistant.py`.
`validate_commit_spec.py` rejected this:

```
file_ownership: nova does not own backend/app/services/assistant.py
file_ownership: nova does not own backend/tests/api/test_assistant.py
```

Both files are Rex's domain. Fix: moved the `assistant.py` wiring into C64 (Rex's
commit). C65 now only touches `rag_logistics.py` and its tests — squarely Nova's domain.

## Issue 2: Evidence graph is unreadable

### Discovery

Eran saw the evidence graph and couldn't understand what it was. It appeared as a
linear diagram with no visual distinction between nodes. No colors, no status
indicators, no hierarchy.

### Root cause analysis

Four compounding problems in `EvidenceGraph.tsx`:

1. **Wrong color map**: `TYPE_COLORS` defined colors for `regulation`, `requirement`,
   `policy`, `evidence` — these are policy-document types from C58's original design.
   The backend sends logistics types: `buyer`, `purchase_order`, `vendor`, `shipment`,
   `product`, `event`. Every node fell through to the gray default
   `{ bg: '#f3f4f6', border: '#9ca3af' }`.

2. **Broken layout**: `typeColumn()` mapped unknown types to
   `Object.keys(TYPE_ORDER).length` — the same column index for all logistics nodes.
   Every node stacked vertically in column 4. That's the "linear diagram."

3. **No status encoding**: `GraphNodeSchema` only had `{id, type, label}`. No way to
   convey that a shipment is delayed (red) vs. delivered (green) vs. in-transit
   (orange).

4. **Too small**: Evidence panel was `lg:w-96` (384px), graph was `h-96` (384px).
   Cramped even if the layout worked.

### Why two commits instead of one

The backend needs to send status metadata before the frontend can color-code by status.
This creates a natural backend/frontend split:

| Commit | Scope | Why separate |
|--------|-------|--------------|
| C66 | Backend: graph metadata | Add `status` and `status_category` fields to `GraphNode`/`GraphNodeSchema`. Map shipment statuses to `done|active|issue`. Backward-compatible (nullable fields). |
| C67 | Frontend: visual overhaul | Replace color scheme, layout algorithm, and sizing. Requires C66's metadata to be deployed. |

C66 couldn't be merged into C65 or C64 — different files (`schemas/assistant.py`,
`api/v1/assistant.py`) and different concern (graph metadata vs. query wiring).

## Execution decisions

### Criteria applied

Per CLAUDE.md: delegation requires "unresolved specialist uncertainty, independent
implementation needed for risk control, or a clearly bounded specialist unit whose
expected value exceeds invocation overhead."

### Assessment per commit

| Commit | Domain owner | Execution | Justification |
|--------|-------------|-----------|---------------|
| C63 | Nova | Claude-direct | Mechanical: add vocabulary words to existing `classify_intent()`, add one literal to `AssistantIntent`, add one field to `IntentRouting`. Fully specified in contract. No prompt engineering or AI design uncertainty. |
| C64 | Rex | Claude-direct | Mechanical: one SQL query with optional WHERE clause, one if-branch in `answer_question()`, one formatter. Follows existing patterns (`_load_shipment`, `_deterministic_fallback`). |
| C65 | Nova | Delegate to Nova | Specialist uncertainty: formatting multi-shipment evidence for an LLM context window requires judgment about token budget, evidence ordering, count disclosure framing, and system prompt wording for list-vs-detail answers. The deterministic fallback design is straightforward but the prompt template is not. |
| C66 | Rex | Claude-direct | Mechanical: add two optional fields to a frozen dataclass and a Pydantic model, populate with a 9-entry status mapping dict. No design uncertainty. |
| C67 | Aria | Delegate to Aria | Bounded specialist unit: ReactFlow layout algorithm (column assignment, hub-and-spoke positioning, gap calculation), CSS color system with status overrides, and responsive sizing. The value of domain expertise in frontend visualization exceeds invocation overhead. |

### Token cost estimate

- Claude-direct (C63, C64, C66): ~0 agent tokens each (orchestrator cost only).
- Delegated (C65, C67): ~45,000 implementor tokens each within budget envelope.
- Total agent cost: ~90,000 tokens for 2 delegated commits vs. ~225,000 if all 5 were delegated.

### What blocked agent invocation during planning

`hooks/tool_cap.json` was stale from C61:
- `commit: "C61"`, `agent: "nova"`, `status: "blocked"`
- `stop_reason: "implementor_token_hard_stop"`
- `known_implementor_tokens: 59694` (vs. 45,000 limit)

This state blocks any `Agent` tool invocation via `tool_cap_start.py`. It will need to
be re-initialized via `initialize_commit_state()` for C63 before execution begins.
The `tool_cap_reset.py` script can clear it:
```powershell
python hooks/tool_cap_reset.py --commit 61 --agent nova --discard-closed
```

## Validator constraints that shaped the specs

1. **File ownership** (`validate_commit_spec.py`): Each domain agent owns specific file
   paths. Nova can't write `assistant.py` (Rex's domain). This forced the C65 scope
   reduction.

2. **Max changed files = 4**: Hard-locked in `LOCKED_BUDGET`. Can't override in the
   spec. This was the same constraint that forced C42A as a letter-suffix commit.

3. **Protocol-spec owner agreement**: The Commit Index table's Assignee column must
   exactly match the spec's Owner field. "claude-direct (nova domain)" failed
   `protocol_owner` validation. Execution mode must be noted separately from ownership.

4. **Max primary files = 2**: Keeps each commit focused. C66 and C67 each have exactly
   2 primary files.

## Files created

| File | Purpose |
|------|---------|
| `commit-specs/commit-63.md` | Spec for logistics_browse intent routing |
| `commit-specs/commit-64.md` | Spec for list_shipments_summary + orchestrator wiring |
| `commit-specs/commit-65.md` | Spec for LLM-grounded browse answer generation |
| `commit-specs/commit-66.md` | Spec for graph node status metadata enrichment |
| `commit-specs/commit-67.md` | Spec for frontend graph visual overhaul |
| `commit-specs/PHASE-3-PLANNING-SESSION.md` | This document |

## Files modified

| File | Changes |
|------|---------|
| `commit-protocol.md` | Added 5 pending rows (C63-C67), Phase 3 section with product result table and execution plan |
| `project-state.json` | Updated phase=3, next_commit=63, status=active, tldr updated |

## Open items for future planning sessions

- The stale `tool_cap.json` from C61 needs clearing before C63 execution.
- Viktor's deferred C46-C55 review wave (OI-21) is still pending.
- If more post-demo issues emerge, they should be planned as C68+ following the same
  execution-honesty criteria applied here.
