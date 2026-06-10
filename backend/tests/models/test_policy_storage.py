"""Integration tests for the C25/C26 policy RAG storage schema.

These tests run against a real PostgreSQL + pgvector database (the docker-compose
``db`` service: db=manifesto, user=manifesto, pass=manifesto on localhost:5432) and
require migrations up to ``0002_rag_storage_hardening`` to be applied
(``alembic upgrade head``).

Each test runs inside its own transaction that is rolled back on teardown, so
tests do not leak rows into each other or require manual cleanup.

Covers:
- Idempotency unique constraint on policy_documents
  (sha256, embedding_provider, embedding_model, embedding_dimensions).
- Chunk ordering unique constraint on policy_chunks (document_id, chunk_index).
- The ready-state trigger: a document cannot become 'ready' while any chunk has
  a NULL embedding, but succeeds once every chunk has a 768-dim embedding.
- Full-text search via the generated search_vector column.
- The HNSW vector index is used for cosine-distance ORDER BY ... LIMIT queries.
- The status CHECK constraint rejects invalid status values.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.policy import PolicyChunk, PolicyDocument

DB_URL = "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"

_DIMS = 768


@pytest_asyncio.fixture
async def session():
    """Yield an AsyncSession bound to a transaction that is rolled back after the test."""
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session_factory = async_sessionmaker(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
            async with session_factory() as sess:
                yield sess
            await trans.rollback()
    finally:
        await engine.dispose()


def _make_document(**overrides) -> PolicyDocument:
    defaults = dict(
        title="Test Policy",
        sha256="a" * 64,
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        embedding_dimensions=_DIMS,
        status="pending",
    )
    defaults.update(overrides)
    return PolicyDocument(**defaults)


def _make_chunk(document_id: str, **overrides) -> PolicyChunk:
    defaults = dict(
        document_id=document_id,
        chunk_index=0,
        content="hello world",
    )
    defaults.update(overrides)
    return PolicyChunk(**defaults)


# ---------------------------------------------------------------------------
# Uniqueness / idempotency constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_document_checksum_profile_rejected(session: AsyncSession):
    """Two documents with the same (sha256, provider, model, dimensions) violate
    uq_policy_documents_checksum_profile."""
    sha = uuid.uuid4().hex + uuid.uuid4().hex[:24]  # 64 hex chars, unique per test run
    doc1 = _make_document(title="Doc 1", sha256=sha)
    session.add(doc1)
    await session.flush()

    doc2 = _make_document(title="Doc 2", sha256=sha)
    session.add(doc2)

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_duplicate_chunk_index_rejected(session: AsyncSession):
    """Two chunks with the same (document_id, chunk_index) violate
    uq_policy_chunks_document_chunk_index."""
    doc = _make_document(sha256=uuid.uuid4().hex + uuid.uuid4().hex[:24])
    session.add(doc)
    await session.flush()

    chunk1 = _make_chunk(doc.id, chunk_index=0, content="first")
    session.add(chunk1)
    await session.flush()

    chunk2 = _make_chunk(doc.id, chunk_index=0, content="duplicate index")
    session.add(chunk2)

    with pytest.raises(IntegrityError):
        await session.flush()


# ---------------------------------------------------------------------------
# Ready-state trigger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ready_status_rejected_when_chunk_missing_embedding(session: AsyncSession):
    """Setting status='ready' while a chunk has embedding=None raises from the trigger."""
    doc = _make_document(sha256=uuid.uuid4().hex + uuid.uuid4().hex[:24])
    session.add(doc)
    await session.flush()

    chunk = _make_chunk(doc.id, chunk_index=0, embedding=None)
    session.add(chunk)
    await session.flush()

    doc.status = "ready"

    with pytest.raises(DBAPIError):
        await session.flush()


@pytest.mark.asyncio
async def test_ready_status_succeeds_when_all_chunks_embedded(session: AsyncSession):
    """Setting status='ready' succeeds once every chunk has a 768-dim embedding."""
    doc = _make_document(sha256=uuid.uuid4().hex + uuid.uuid4().hex[:24])
    session.add(doc)
    await session.flush()

    chunk = _make_chunk(doc.id, chunk_index=0, embedding=[0.1] * _DIMS)
    session.add(chunk)
    await session.flush()

    doc.status = "ready"
    await session.flush()  # must not raise

    await session.refresh(doc)
    assert doc.status == "ready"


# ---------------------------------------------------------------------------
# Full-text search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_vector_full_text_query(session: AsyncSession):
    """search_vector @@ plainto_tsquery(...) returns the expected chunk."""
    doc = _make_document(sha256=uuid.uuid4().hex + uuid.uuid4().hex[:24])
    session.add(doc)
    await session.flush()

    chunk = _make_chunk(
        doc.id,
        chunk_index=0,
        content="The quick brown fox jumps over the lazy dog",
    )
    session.add(chunk)
    await session.flush()

    result = await session.execute(
        text(
            "SELECT id FROM policy_chunks "
            "WHERE document_id = :doc_id "
            "AND search_vector @@ plainto_tsquery('english', :q)"
        ),
        {"doc_id": doc.id, "q": "fox jumps"},
    )
    rows = result.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == chunk.id


# ---------------------------------------------------------------------------
# HNSW vector index usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hnsw_index_used_for_vector_search(session: AsyncSession):
    """EXPLAIN on an ORDER BY embedding <=> :vec LIMIT k query references the
    HNSW index ix_policy_chunks_embedding_hnsw."""
    doc = _make_document(sha256=uuid.uuid4().hex + uuid.uuid4().hex[:24])
    session.add(doc)
    await session.flush()

    for i in range(5):
        session.add(_make_chunk(doc.id, chunk_index=i, content=f"chunk {i}", embedding=[0.1 * i] * _DIMS))
    await session.flush()

    query_vec = "[" + ",".join(["0.05"] * _DIMS) + "]"

    # The planner only chooses the HNSW index over a small table when seq scan
    # is sufficiently discouraged; force index usage to deterministically
    # exercise the index in this small test dataset.
    await session.execute(text("SET LOCAL enable_seqscan = off"))

    result = await session.execute(
        text(
            "EXPLAIN SELECT id FROM policy_chunks "
            "ORDER BY embedding <=> CAST(:qvec AS vector) LIMIT 3"
        ),
        {"qvec": query_vec},
    )
    plan_lines = [row[0] for row in result.fetchall()]
    plan_text = "\n".join(plan_lines)
    assert "ix_policy_chunks_embedding_hnsw" in plan_text, plan_text


# ---------------------------------------------------------------------------
# CHECK constraint on status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_status_rejected_by_check_constraint(session: AsyncSession):
    """An invalid status value violates policy_document_status_check."""
    doc = _make_document(sha256=uuid.uuid4().hex + uuid.uuid4().hex[:24], status="bogus")
    session.add(doc)

    with pytest.raises(DBAPIError):
        await session.flush()
