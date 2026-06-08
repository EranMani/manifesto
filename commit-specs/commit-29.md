# Commit 29 — `rag-policy-pipeline` · Nova

**Phase:** 2C — Retrieval and Grounded Generation
**Assignee:** Nova (AI/ML Engineer)
**Depends on:** C27 (document-ingestion)

---

## context

```
tier0:
  - .claude/agents/ai-engineer.md (Current State header only — first 50 lines)

tier1:
  - backend/app/services/rag_policy.py  # C16 stub to replace
  - backend/app/services/llm.py         # C25 service contracts
  - backend/app/models/policy.py        # C26 retrieval fields
  - backend/app/services/ingestion.py   # C27 metadata/chunk invariants

tier2:
  - manifesto-spec.md (§6 RAG Pipeline — Policy Chat)

forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/models/
  - backend/alembic/

estimated_reads: 5
estimated_edits: 3   # rag_policy.py, tests, evaluation fixture
fits_single_agent: true
```

---

## What

Implement a production-oriented policy RAG pipeline with hybrid retrieval, bounded
context, explicit grounding, validated source references, and measurable quality.

---

## Files to Change

| File | Type | Description |
|---|---|---|
| `backend/app/services/rag_policy.py` | edit | Implement hybrid retrieval, grounding, streaming, and source validation |
| `backend/tests/services/test_rag_policy.py` | new | Retrieval, prompt, stream, and abstention tests |
| `backend/tests/evals/policy_rag.json` | new | Versioned initial evaluation dataset |

---

## Public Contract

```python
async def answer_policy_question(
    *,
    query: str,
    history: Sequence[ChatMessage],
    llm: LLMService,
    embeddings: EmbeddingService,
    db: AsyncSession,
) -> AsyncIterator[PolicyEvent]:
    ...
```

Events are provider-neutral typed values: text delta, sources, completion, or normalized
failure. A source contains stable document/chunk IDs, title, page/section when known,
retrieval score, and the prompt label used by the model.

---

## Retrieval

1. Normalize and validate the query without rewriting its meaning.
2. Embed with the deployment-wide query embedding profile from C25.
3. Retrieve a wider candidate pool from ready documents using both HNSW cosine search and
   PostgreSQL full-text ranking.
4. Fuse rankings with reciprocal-rank fusion, then diversify by document and adjacent
   chunk so one repeated section cannot consume the whole context.
5. Apply a calibrated minimum evidence threshold and a strict token budget. Select about
   4-8 final chunks; top-k is configuration, not a magic constant.
6. Preserve deterministic ordering and stable source labels (`S1`, `S2`, ...).

Vector-only fallback is allowed if a query has no useful lexical terms. Retrieval always
filters to `status='ready'` and the active embedding provider/model/dimension.

---

## Grounding

- Delimit policy excerpts as untrusted source data and instruct the model to ignore any
  instructions contained inside them.
- Include the current question and a bounded server-supplied history window measured by
  tokens, not simply six arbitrary messages.
- Require factual claims to carry inline source labels such as `[S2]`.
- If evidence is below threshold or does not answer the question, return a clear
  insufficient-evidence answer without calling the result authoritative.
- Accumulate only source labels actually emitted by the model, validate them against the
  retrieved map, and emit structured sources. Never accept model-invented IDs/titles.
- Set low, explicit generation randomness and a maximum output budget.

---

## Streaming and Failure Semantics

- Stream text as received and separately emit validated sources at completion.
- Cancellation propagates immediately to the provider.
- A retrieval/provider failure before output becomes a normalized failure event.
- A failure after output has started is terminal and is never retried as a second answer.

---

## Test Gate

Add a small versioned dataset containing answerable, unanswerable, paraphrased, ambiguous,
and prompt-injection-style questions. Measure at minimum:

- retrieval hit rate / MRR against expected documents
- answer abstention on unanswerable questions
- citation validity (every emitted source exists and was retrieved)
- context token budget and latency

Thresholds are recorded as baseline gates, not claimed as universal production targets.

---

## Done When

- [ ] Hybrid retrieval is deterministic and profile-filtered
- [ ] The prompt cannot confuse document text with system instructions
- [ ] Unanswerable questions abstain in tests
- [ ] Streamed citations are structured, validated, and traceable to exact chunks
- [ ] Unit tests and the initial offline evaluation pass

---

## Handoffs Out

→ Rex (C30): consume typed policy events and map them to the frozen SSE v1 contract.

→ Rex (C31): persist validated structured sources, not model-generated title strings.
