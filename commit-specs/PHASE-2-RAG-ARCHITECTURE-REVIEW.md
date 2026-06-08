# Phase 2 RAG Architecture Review

**Reviewed:** 2026-06-08
**Scope:** Pending Phase 2 plan, now cleanly numbered C24-C34
**Verdict:** Original plan was directionally sound but not implementation-safe.

## Blocking Findings Corrected

1. **Embedding space was coupled to chat provider.** A corpus cannot be indexed with one
   model and queried with another merely because dimensions happen to match. Embeddings
   are now a deployment-wide profile independent of Ollama/OpenAI generation choice.
2. **The dependency graph was invalid.** The upload route depended on ingestion while the
   protocol placed them in parallel. Correct parallel work is C28 with C29 after C27.
3. **Specs described existing files/tables as new.** Documents routes, chat routes,
   conversations, messages, models, and migration DDL already exist. Revised specs extend
   the current repository instead of duplicating it.
4. **The LLM and ingestion work required Rex-owned dependency, config, model, and
   migration changes.** C24 and C26 preserve domain ownership and make the Nova-owned
   C25/C27 gates independently passable.
5. **Citations were transient title strings.** Structured source references are now
   validated against retrieval results and persisted with title/page snapshots.
6. **Client-supplied history was trusted.** History is now loaded server-side from an
   owner-scoped conversation and bounded by tokens.
7. **SSE had no protocol.** The new contract has versioned named events, JSON payloads,
   cancellation, heartbeat, terminal-state, and normalized-error semantics.
8. **Ingestion was not idempotent or recoverable.** Checksum/profile identity, document
   states, advisory locking, short transactions, batched embeddings, and rollback rules
   now define retry behavior.
9. **The first revision harmed protocol readability.** Lettered commits were inserted
   before and after C24. Because no Phase 2 implementation commit had started, the plan
   was renumbered once as the contiguous sequence C24-C34. Future scope additions should
   append or deliberately renumber pending work rather than accumulate `a/b/c` suffixes.
10. **The first embedding default weakened local deployment.** An OpenAI-only
    1536-dimensional profile conflicted with the Ollama/on-premise product goal. Phase 2
    now standardizes storage at 768 dimensions: Ollama uses `nomic-embed-text`, while
    OpenAI uses `text-embedding-3-small` with `dimensions=768`. Provider/model changes
    still require full re-index because equal dimensions do not imply a shared vector
    space.

## Production RAG Design

### Indexing

- Structure-aware, tokenizer-bounded chunks retain document/page/section provenance.
- Embeddings are batched and profile-validated.
- HNSW supports an initially empty and continuously growing corpus better than the
  pre-created IVFFlat index.
- PostgreSQL full-text search complements semantic retrieval.

### Retrieval

- Retrieve broad vector and lexical candidates.
- Fuse with reciprocal-rank fusion.
- Diversify repeated/adjacent evidence and fit a strict token budget.
- Apply an evidence threshold and abstain when policy support is missing.

### Grounding and Citations

- Retrieved text is explicitly untrusted and delimited from system instructions.
- The model cites stable source labels; the service validates labels against retrieved
  chunks before emitting source objects.
- Historical messages preserve exact provenance through citation rows and snapshots.

### Reliability

- No database transaction spans parsing, embedding, or generation network calls.
- Retries occur only where idempotent and never replay a partially streamed answer.
- Client message IDs prevent duplicate sends.
- Disconnects cancel upstream work and produce durable cancelled/failed states.

### Quality

Phase 2 now requires a small versioned evaluation set covering answerable, unanswerable,
paraphrased, ambiguous, and prompt-injection-style questions. Retrieval quality,
abstention, citation validity, context size, and latency become measured properties.

## Explicit Non-Goals

- OCR for scanned PDFs
- cross-encoder reranking
- durable external ingestion queue
- document viewer/download links
- tenant-level policy ACLs beyond the current single-company role model

These are extension points, not hidden assumptions. Before calling the system
multi-tenant or high-volume production ready, add tenant keys/row-level authorization,
a durable job queue, object storage, malware scanning, rate limits, tracing, and load/eval
gates.

## GraphRAG Boundary

The policy-document pipeline should not be converted to GraphRAG by default. Its primary
questions are local factual lookups over a modest document corpus, where hybrid
vector/lexical retrieval with structured citations is simpler and cheaper. Microsoft
GraphRAG is aimed at extracting entities, relationships, claims, communities, and
summaries from unstructured text; that machinery becomes useful only if policy questions
need cross-document entity reasoning or corpus-wide thematic analysis.

The connected vendor, shipment, product, and category domain is different. It already
forms an authoritative graph in normalized PostgreSQL foreign keys. Phase 3 should exploit
that graph explicitly, but should not immediately duplicate it into Neo4j or an
LLM-extracted knowledge graph. See `PHASE-3-GRAPH-RAG-DESIGN.md`.

## Primary References

- OpenAI streaming responses:
  https://platform.openai.com/docs/guides/streaming-responses
- OpenAI embeddings:
  https://platform.openai.com/docs/api-reference/embeddings
- Ollama API and streaming:
  https://docs.ollama.com/api
- pgvector HNSW and IVFFlat:
  https://github.com/pgvector/pgvector
