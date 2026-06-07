# Commit 25 — `document-ingestion` · Nova

**Phase:** 2B — Ingestion Pipeline
**Assignee:** Nova (AI/ML Engineer)
**Depends on:** C24 (llm-service-impl — needs working `embed()`), C23 (policy_chunks table must exist with matching embedding dimension)

---

## context

```
tier0:
  - .claude/agents/ai-engineer.md (Current State header — first 50 lines)

tier1:
  - backend/app/services/ingestion.py   # C16 stub
  - backend/app/services/llm.py         # Nova's own C24 work — confirm embed() signature/dimension
  - backend/app/models/policy.py        # PolicyDocument/PolicyChunk models from C23

tier2:
  - manifesto-spec.md (§10 Document Ingestion, lines ~406-421)

forbidden:
  - frontend/
  - backend/app/api/        # Rex builds upload routes in C26 — Nova provides the pipeline function only
  - backend/app/models/
  - backend/alembic/

estimated_reads: 3
estimated_edits: 1   # ingestion.py
fits_single_agent: true
```

---

## What

Implement the ingestion pipeline: extract text from an uploaded document, chunk it,
embed each chunk, and store chunks + embeddings. Exposed as a single async function
that C26's upload route will call — Nova does not write the route itself.

---

## Files to Change

| File | Type | Description |
|---|---|---|
| `backend/app/services/ingestion.py` | edit | Implement extraction → chunking → embedding → storage pipeline |

---

## Pipeline (per manifesto-spec.md §10)

```
Validate file type (PDF, DOCX, TXT, MD)
  → Extract text:  PDF → PyMuPDF · DOCX → python-docx · TXT/MD → read directly
  → Chunk: RecursiveCharacterTextSplitter, 512 tokens, 50 token overlap
  → Embed each chunk via LLMService.embed()
  → Insert into policy_chunks (document_id, chunk_index, content, embedding)
  → Return { document_id, title, chunk_count }
```

Suggested entry point signature (Nova may refine — this is the contract C26 builds against):
```python
async def ingest_document(
    file_bytes: bytes,
    filename: str,
    title: str,
    uploaded_by: UUID,
    db: AsyncSession,
) -> IngestResult:  # { document_id: UUID, title: str, chunk_count: int }
```

---

## Cross-Domain Note — New Dependencies

`PyMuPDF` and `python-docx` are not yet in `backend/pyproject.toml`. Nova does not own
that file (Rex's domain). Raise a cross-domain finding to Rex listing the exact packages
and versions needed — do not edit `pyproject.toml` directly.

---

## Done When

- [ ] `ingest_document()` extracts text correctly from PDF, DOCX, TXT, and MD inputs
- [ ] Chunks are ~512 tokens with ~50 token overlap
- [ ] Each chunk is embedded via `LLMService.embed()` using the provider/dimension fixed in C24
- [ ] Chunks are persisted to `policy_chunks` with correct `document_id` and sequential `chunk_index`
- [ ] Returns `{ document_id, title, chunk_count }`
- [ ] Cross-domain finding raised to Rex for new `pyproject.toml` dependencies

---

## Handoffs Out

→ Rex (C26): `ingest_document(file_bytes, filename, title, uploaded_by, db) -> IngestResult`
is the function your upload route calls. It handles extraction through storage — your route
only needs to validate the upload, call this, and return the result.
