# Commit 76 - `concise-shipment-summary` - Nova

**Phase:** Phase 3 — Assistant Hardening
**Owner:** nova
**Depends on:** C75
**Estimated diff lines:** 60
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Single-shipment logistics answers render as a concise bullet-point summary of key
facts (status, route, vendor, products, delays) instead of verbose LLM-generated
paragraphs, producing a scannable companion to the evidence graph.

---

## Semantic Fit Review

- **Atomic outcome:** The answer format changes from free-form prose to structured
  bullet points. The graph, evidence retrieval, and routing are untouched.
- **Failure boundary:** Only `_SYSTEM_PROMPT` and `_deterministic_fallback()` change.
  LLM generation and graph projection remain stable.
- **Budget rationale:** Two string-level edits in one file. Existing tests assert
  content presence (tracking code, status, delay reason), not formatting, so they pass
  without modification. One optional new test verifies bullet formatting.

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
  - backend/app/services/rag_logistics.py

initial_context:
  - commit-specs/commit-76.md
  - backend/app/services/rag_logistics.py
  - backend/tests/services/test_rag_logistics.py

forbidden:
  - frontend/
  - hooks/
  - backend/app/api/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Update `_SYSTEM_PROMPT` to instruct concise bullet-point format; rewrite `_deterministic_fallback()` to produce markdown bullet list |

---

## Contract

**Input:** Same `ProcurementEvidence` dataclass — no schema changes.

**Output — LLM path:** The system prompt instructs the model to respond with a short
markdown bullet list covering: status, origin → destination, vendor, products (if any),
expected/actual arrival, delay reason (if any). No headers, no paragraphs.

**Output — Fallback path:** `_deterministic_fallback()` produces an equivalent markdown
bullet list using `- **Label:** value` format, so the answer is visually identical
whether the LLM is available or not.

**Unchanged:** `LogisticsAnswer` dataclass, `ProcurementGraph`, graph projection,
`AssistantQueryResponse` schema, follow-up questions.

---

## Environment Prerequisites

- Backend Python environment with `app.services.rag_logistics` importable.
- Docker DB for integration tests (if running full test suite).

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest backend/tests/services/test_rag_logistics.py -q
```

---

## Focused Tests

- Happy path: existing `test_grounded_answer_provider_failure_returns_deterministic_fallback`
  continues to pass (asserts tracking_code, "delayed", "Customs hold", product name,
  order number, buyer name all present in answer).
- Boundary: fallback output uses markdown bullet syntax (`- **`).
- Regression: graph evidence is still returned alongside the text answer.

---

## Done When

- [ ] `_SYSTEM_PROMPT` instructs concise bullet-point format.
- [ ] `_deterministic_fallback()` produces markdown bullet list.
- [ ] Existing fallback tests pass without modification.
- [ ] Verification command passes.

---

## Developer Test Checkpoint

**Next milestone:** Post-Phase 3 hardening conclusion.

---

## Not In This Commit

- Browse/multi-shipment answer format (separate concern, `_BROWSE_SYSTEM_PROMPT`).
- Frontend layout changes (markdown bullet rendering already works via `ReactMarkdown`).
- Mixed-answer format changes (policy + logistics combined answers).

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
