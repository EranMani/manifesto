# Commit 27 — `document-ingestion` · Nova

**Phase:** 2B — Ingestion Pipeline
**Assignee:** Nova (AI/ML Engineer)
**Depends on:** C25 (llm-service-impl), C26 (rag-storage-hardening)

---

## context

```
tier0:
  - .claude/agents/ai-engineer.md (Current State header only — first 50 lines)

tier1:
  - backend/app/services/ingestion.py   # C16 stub to replace
  - backend/app/services/llm.py         # C25 EmbeddingService contract
  - backend/app/models/policy.py        # C26 status/profile/provenance fields

tier2:
  - manifesto-spec.md (§10 Document Ingestion)

forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/models/
  - backend/alembic/
  - backend/app/core/

estimated_reads: 4
estimated_edits: 2   # ingestion.py + parser/chunker tests and fixtures
fits_single_agent: true
```

---

## What

Build a deterministic, idempotent ingestion service that extracts document structure,
creates token-aware chunks, batches embeddings, and atomically publishes a searchable
document.

---

## Files to Change

| File | Type | Description |
|---|---|---|
| `backend/app/services/ingestion.py` | edit | Implement deterministic extraction, chunking, embedding, and publication |
| `backend/tests/services/test_ingestion.py` | new | Parser, chunker, idempotency, and failure tests |
| `backend/tests/fixtures/documents/` | new | Minimal PDF, DOCX, TXT, and MD fixtures |

---

## Contract

```python
async def ingest_document(
    *,
    document_id: UUID,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    db: AsyncSession,
    embeddings: EmbeddingService,
) -> IngestResult:
    ...
```

The route creates or resolves the idempotent `policy_documents` row. The service owns the
`processing -> ready|failed` transition and returns document ID, status, and chunk count.

---

## Pipeline

1. Verify the stored checksum/profile and acquire a per-document advisory lock so two
   workers cannot ingest the same row concurrently.
2. Extract PDF pages with PyMuPDF, DOCX paragraphs/headings/tables with `python-docx`, and
   strict UTF-8 text for TXT/MD. Reject encrypted, empty, corrupt, or image-only files with
   a typed error; OCR is explicitly deferred.
3. Normalize Unicode and whitespace without destroying headings, lists, page boundaries,
   or paragraph provenance. Treat all document text as untrusted data.
4. Split by structure first, then by the configured tokenizer. Target about 450 tokens,
   hard-cap at 600, and overlap 60 tokens only across adjacent chunks in the same section.
5. Attach page, section, token count, and stable chunk index metadata.
6. Batch embeddings with bounded concurrency and validate the active profile/dimension.
7. In one short database transaction, replace this document's chunks, set `chunk_count`,
   and publish `status='ready'`. Do not hold a transaction open during parsing or network
   calls.

---

## Operational Requirements

- CPU-heavy parsing runs in a worker thread so the event loop remains responsive.
- Chunking is deterministic: the same bytes and profile produce the same ordered chunks.
- Memory and page/paragraph counts are bounded. The route's byte limit is not the only
  defense against decompression bombs or pathological documents.
- A failed attempt leaves no partial searchable chunks and records a sanitized error.
- Retries are safe and do not create duplicate documents or chunks.

---

## Test Gate

- PDF, DOCX, TXT, and MD extraction including headings, pages, tables, and Unicode.
- Empty, encrypted, corrupt, image-only, invalid UTF-8, oversized structure, and duplicate
  ingestion cases.
- Token hard cap, overlap, deterministic output, metadata, and sequential indices.
- Batched embedding order, dimension mismatch, rollback, retry, and concurrent lock path.

---

## Done When

- [ ] A fixture of each supported type reaches `ready` with deterministic chunks
- [ ] No partial chunk set is visible after any injected failure
- [ ] Duplicate/retried ingestion is idempotent
- [ ] Unit tests use fake embeddings; one opt-in database integration test verifies pgvector
  insertion and status transitions.

---

## Handoffs Out

→ Rex (C28): create/resolve the document row and call the frozen `ingest_document()` contract;
the service owns `processing → ready|failed`.

→ Nova (C29): retrieval may assume deterministic chunk indexes and page/section metadata.
