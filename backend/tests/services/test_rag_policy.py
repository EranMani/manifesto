"""Tests for backend/app/services/rag_policy.py — query normalization, embedding,
vector candidate retrieval, and grounded policy/mixed answer generation.

The minimal evidence retrieval tests run against a real PostgreSQL database
(the docker-compose ``db`` service, resolved via DATABASE_URL inside the
backend container). Each test runs inside its own transaction that is rolled
back on teardown.

Grounded-answer tests use async generator stubs for LLMService.chat() to
avoid any provider dependency.
"""

import math
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.policy import PolicyChunk, PolicyDocument
from app.services.llm import EmbeddingProfile
from app.services.rag_policy import (
    EmptyQueryError,
    MIN_EVIDENCE_SCORE,
    MixedAnswer,
    PolicyAnswer,
    PolicyChunkCandidate,
    RAGPolicy,
    generate_grounded_mixed_answer,
    generate_grounded_policy_answer,
)

ACTIVE_PROFILE = EmbeddingProfile(provider="ollama", model="nomic-embed-text", dimensions=768)

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)


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


async def _make_document(session: AsyncSession, *, title: str, status: str = "ready", profile: EmbeddingProfile = ACTIVE_PROFILE) -> PolicyDocument:
    document = PolicyDocument(
        title=title,
        status=status,
        embedding_provider=profile.provider,
        embedding_model=profile.model,
        embedding_dimensions=profile.dimensions,
    )
    session.add(document)
    await session.flush()
    return document


async def _make_chunk(
    session: AsyncSession,
    document: PolicyDocument,
    *,
    chunk_index: int,
    content: str,
    embedding: list[float],
    page_number: int | None = 1,
    section: str | None = "Leave Policy",
) -> PolicyChunk:
    chunk = PolicyChunk(
        document_id=document.id,
        chunk_index=chunk_index,
        content=content,
        embedding=embedding,
        page_number=page_number,
        section=section,
    )
    session.add(chunk)
    await session.flush()
    return chunk


def _unit_vector(index: int, dimensions: int = 768) -> list[float]:
    """A 768-dim one-hot vector, used so cosine similarity is exactly 1.0 or 0.0."""
    vector = [0.0] * dimensions
    vector[index] = 1.0
    return vector


class FixedQueryEmbeddingService:
    """Embedding test double for retrieve_evidence: embed_query returns a fixed vector."""

    def __init__(self, query_vector: list[float], profile: EmbeddingProfile = ACTIVE_PROFILE) -> None:
        self.profile = profile
        self._query_vector = query_vector

    async def embed_query(self, text: str) -> list[float]:
        return self._query_vector


class FakeEmbeddingService:
    """Deterministic embedding test double; tracks calls, no provider SDKs involved."""

    def __init__(self, dimensions: int = 8, profile: EmbeddingProfile = ACTIVE_PROFILE) -> None:
        self._dimensions = dimensions
        self.profile = profile
        self.embed_documents_calls: list[list[str]] = []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embed_documents_calls.append(list(texts))
        return [[float(len(t) % 7) + 0.1 * i for i in range(self._dimensions)] for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0]


def _chunk(
    chunk_id: int,
    chunk_index: int,
    embedding: list[float],
    status: str = "ready",
    profile: EmbeddingProfile = ACTIVE_PROFILE,
) -> PolicyChunkCandidate:
    return PolicyChunkCandidate(
        chunk_id=chunk_id,
        document_id=1,
        chunk_index=chunk_index,
        page_number=1,
        section="Leave Policy",
        text=f"chunk {chunk_index}",
        embedding=embedding,
        status=status,
        embedding_provider=profile.provider,
        embedding_model=profile.model,
        embedding_dimensions=profile.dimensions,
    )


class TestQueryEmbedding:
    @pytest.mark.asyncio
    async def test_query_embedding_normalizes_and_embeds_once(self) -> None:
        embeddings = FakeEmbeddingService(dimensions=8)
        policy = RAGPolicy(embeddings=embeddings)

        vector = await policy.embed_query("  What   is\tthe\n\nleave policy?  ")

        assert embeddings.embed_documents_calls == [["What is the leave policy?"]]
        assert len(vector) == 8

    @pytest.mark.asyncio
    async def test_query_embedding_rejects_blank_input(self) -> None:
        embeddings = FakeEmbeddingService(dimensions=8)
        policy = RAGPolicy(embeddings=embeddings)

        with pytest.raises(EmptyQueryError):
            await policy.embed_query("   \n\t  ")

        assert embeddings.embed_documents_calls == []


class TestFetchVectorCandidates:
    def test_vector_candidates_cosine_ordering_is_deterministic(self) -> None:
        embeddings = FakeEmbeddingService(dimensions=3)
        policy = RAGPolicy(embeddings=embeddings)
        query_vector = [1.0, 0.0, 0.0]

        candidates = [
            _chunk(1, chunk_index=0, embedding=[0.0, 1.0, 0.0]),  # orthogonal -> 0.0
            _chunk(2, chunk_index=1, embedding=[1.0, 0.0, 0.0]),  # identical -> 1.0
            _chunk(3, chunk_index=2, embedding=[0.5, 0.5, 0.0]),  # partial -> ~0.707
        ]

        results = policy.fetch_vector_candidates(query_vector, candidates, top_k=5)

        assert [r["chunk"]["chunk_id"] for r in results] == [2, 3, 1]
        assert results[0]["score"] == pytest.approx(1.0)
        assert results[1]["score"] == pytest.approx(0.7071, rel=1e-3)
        assert results[2]["score"] == pytest.approx(0.0)

    def test_vector_candidates_cosine_ordering_breaks_ties_by_chunk_index(self) -> None:
        embeddings = FakeEmbeddingService(dimensions=3)
        policy = RAGPolicy(embeddings=embeddings)
        query_vector = [1.0, 0.0, 0.0]

        candidates = [
            _chunk(10, chunk_index=5, embedding=[1.0, 0.0, 0.0]),
            _chunk(11, chunk_index=2, embedding=[1.0, 0.0, 0.0]),
        ]

        results = policy.fetch_vector_candidates(query_vector, candidates, top_k=5)

        assert [r["chunk"]["chunk_id"] for r in results] == [11, 10]

    def test_vector_candidates_wrong_profile_and_non_ready_documents_are_excluded(self) -> None:
        embeddings = FakeEmbeddingService(dimensions=3, profile=ACTIVE_PROFILE)
        policy = RAGPolicy(embeddings=embeddings)
        query_vector = [1.0, 0.0, 0.0]
        other_profile = EmbeddingProfile(provider="openai", model="text-embedding-3-small", dimensions=768)

        candidates = [
            _chunk(1, chunk_index=0, embedding=[1.0, 0.0, 0.0], status="ready"),
            _chunk(2, chunk_index=1, embedding=[1.0, 0.0, 0.0], status="processing"),
            _chunk(3, chunk_index=2, embedding=[1.0, 0.0, 0.0], status="failed"),
            _chunk(
                4,
                chunk_index=3,
                embedding=[1.0, 0.0, 0.0],
                profile=other_profile,
            ),
        ]

        results = policy.fetch_vector_candidates(query_vector, candidates, top_k=5)

        assert [r["chunk"]["chunk_id"] for r in results] == [1]

    def test_vector_candidates_top_k_truncates_results(self) -> None:
        embeddings = FakeEmbeddingService(dimensions=3)
        policy = RAGPolicy(embeddings=embeddings)
        query_vector = [1.0, 0.0, 0.0]

        candidates = [_chunk(i, chunk_index=i, embedding=[1.0, 0.0, 0.0]) for i in range(10)]

        results = policy.fetch_vector_candidates(query_vector, candidates, top_k=3)

        assert len(results) == 3


class TestRetrieveEvidence:
    @pytest.mark.asyncio
    async def test_ready_matching_chunks_return_source_labels(self, session: AsyncSession) -> None:
        query_vector = _unit_vector(0)
        document = await _make_document(session, title="Leave Policy Handbook")
        chunk = await _make_chunk(
            session,
            document,
            chunk_index=0,
            content="Employees get 20 days of annual leave.",
            embedding=query_vector,
            page_number=3,
            section="Leave Policy",
        )

        policy = RAGPolicy(embeddings=FixedQueryEmbeddingService(query_vector))
        evidence = await policy.retrieve_evidence(session, "How much annual leave do I get?")

        assert len(evidence) == 1
        assert evidence[0]["source_title"] == "Leave Policy Handbook"
        assert evidence[0]["document_id"] == document.id
        assert evidence[0]["chunk_id"] == chunk.id
        assert evidence[0]["section"] == "Leave Policy"
        assert evidence[0]["page_number"] == 3
        assert evidence[0]["excerpt"] == "Employees get 20 days of annual leave."
        assert evidence[0]["score"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_wrong_profile_and_non_ready_documents_are_excluded(self, session: AsyncSession) -> None:
        query_vector = _unit_vector(0)
        other_profile = EmbeddingProfile(provider="openai", model="text-embedding-3-small", dimensions=768)

        ready_document = await _make_document(session, title="Ready Policy")
        await _make_chunk(session, ready_document, chunk_index=0, content="ready chunk", embedding=query_vector)

        processing_document = await _make_document(session, title="Processing Policy", status="processing")
        await _make_chunk(session, processing_document, chunk_index=0, content="processing chunk", embedding=query_vector)

        other_profile_document = await _make_document(session, title="Other Profile Policy", profile=other_profile)
        await _make_chunk(session, other_profile_document, chunk_index=0, content="other profile chunk", embedding=query_vector)

        policy = RAGPolicy(embeddings=FixedQueryEmbeddingService(query_vector))
        evidence = await policy.retrieve_evidence(session, "What is the policy?")

        assert [e["document_id"] for e in evidence] == [ready_document.id]

    @pytest.mark.asyncio
    async def test_weak_evidence_below_threshold_is_discarded(self, session: AsyncSession) -> None:
        query_vector = _unit_vector(0)
        weak_embedding = [0.2, math.sqrt(1 - 0.2**2)] + [0.0] * 766

        document = await _make_document(session, title="Weak Match Policy")
        await _make_chunk(session, document, chunk_index=0, content="barely related chunk", embedding=weak_embedding)

        policy = RAGPolicy(embeddings=FixedQueryEmbeddingService(query_vector))
        evidence = await policy.retrieve_evidence(session, "What is the policy?")

        assert evidence == []
        assert 0.2 < MIN_EVIDENCE_SCORE

    @pytest.mark.asyncio
    async def test_result_count_is_bounded(self, session: AsyncSession) -> None:
        query_vector = _unit_vector(0)
        document = await _make_document(session, title="Big Policy")
        for chunk_index in range(6):
            await _make_chunk(
                session,
                document,
                chunk_index=chunk_index,
                content=f"chunk {chunk_index}",
                embedding=query_vector,
            )

        policy = RAGPolicy(embeddings=FixedQueryEmbeddingService(query_vector))
        evidence = await policy.retrieve_evidence(session, "What is the policy?")

        assert len(evidence) == 5


# ---------------------------------------------------------------------------
# Grounded answer generation stubs
# ---------------------------------------------------------------------------


class _StubLLMService:
    """Minimal LLM stub that returns a fixed answer string from chat()."""

    def __init__(self, answer: str) -> None:
        self._answer = answer

    async def chat(self, messages: object, *, stream: bool = True) -> AsyncGenerator[str, None]:
        answer = self._answer

        async def _gen() -> AsyncGenerator[str, None]:
            yield answer

        return _gen()


class _ErrorLLMService:
    """LLM stub that raises LLMError on chat() to exercise the fallback path."""

    async def chat(self, messages: object, *, stream: bool = True) -> AsyncGenerator[str, None]:
        from app.services.llm import LLMError

        raise LLMError("provider unavailable")


class _StubLogisticsAnswer:
    """Minimal logistics answer stub with a graph attribute."""

    def __init__(self, answer: str, graph: object) -> None:
        self.answer = answer
        self.graph = graph


class _StubProcurementEvidence:
    """Placeholder evidence object — not inspected by generate_grounded_mixed_answer."""


# ---------------------------------------------------------------------------
# TestGroundedPolicyAnswer
# ---------------------------------------------------------------------------


class TestGroundedPolicyAnswer:
    @pytest.mark.asyncio
    async def test_grounded_answer_returns_citations(self, session: AsyncSession) -> None:
        """When evidence is found, the answer comes from the LLM and citations trace to stored chunks."""
        query_vector = _unit_vector(0)
        document = await _make_document(session, title="Leave Policy Handbook")
        chunk = await _make_chunk(
            session,
            document,
            chunk_index=0,
            content="Employees receive 20 days of annual leave.",
            embedding=query_vector,
            page_number=5,
            section="Leave Entitlement",
        )

        llm = _StubLLMService("You are entitled to 20 days of annual leave.")
        embeddings = FixedQueryEmbeddingService(query_vector)

        result = await generate_grounded_policy_answer(session, llm, "How much leave do I get?", embeddings)  # type: ignore[arg-type]

        assert isinstance(result, PolicyAnswer)
        assert result.answer == "You are entitled to 20 days of annual leave."
        assert len(result.citations) == 1
        assert result.citations[0]["source_title"] == "Leave Policy Handbook"
        assert result.citations[0]["chunk_id"] == chunk.id
        assert result.citations[0]["section"] == "Leave Entitlement"
        assert result.citations[0]["page_number"] == 5

    @pytest.mark.asyncio
    async def test_grounded_answer_insufficient_evidence_is_explicit(self, session: AsyncSession) -> None:
        """When no evidence meets the threshold the answer is an explicit not-found statement."""
        query_vector = _unit_vector(0)

        # Insert a chunk with a weak (below-threshold) embedding so retrieve_evidence returns [].
        weak_embedding = [0.2, math.sqrt(1 - 0.2**2)] + [0.0] * 766
        document = await _make_document(session, title="Unrelated Policy")
        await _make_chunk(
            session,
            document,
            chunk_index=0,
            content="Unrelated content.",
            embedding=weak_embedding,
        )

        llm = _StubLLMService("should not be called")
        embeddings = FixedQueryEmbeddingService(query_vector)

        result = await generate_grounded_policy_answer(session, llm, "What is the leave policy?", embeddings)  # type: ignore[arg-type]

        assert isinstance(result, PolicyAnswer)
        assert "not found" in result.answer.lower()
        assert result.citations == []

    @pytest.mark.asyncio
    async def test_grounded_answer_llm_error_returns_excerpt_summary(self, session: AsyncSession) -> None:
        """On LLMError the answer is a deterministic excerpt summary; citations still trace to chunks."""
        query_vector = _unit_vector(0)
        document = await _make_document(session, title="Code of Conduct")
        chunk = await _make_chunk(
            session,
            document,
            chunk_index=0,
            content="All employees must adhere to the code of conduct.",
            embedding=query_vector,
            page_number=1,
            section="Introduction",
        )

        llm = _ErrorLLMService()
        embeddings = FixedQueryEmbeddingService(query_vector)

        result = await generate_grounded_policy_answer(session, llm, "What conduct is expected?", embeddings)  # type: ignore[arg-type]

        assert isinstance(result, PolicyAnswer)
        # The fallback must reference the source title, not invented content.
        assert "Code of Conduct" in result.answer
        assert "All employees must adhere" in result.answer
        # Citations are still returned — the error is in generation, not retrieval.
        assert len(result.citations) == 1
        assert result.citations[0]["chunk_id"] == chunk.id


# ---------------------------------------------------------------------------
# TestGroundedMixedAnswer
# ---------------------------------------------------------------------------


class TestGroundedMixedAnswer:
    @pytest.mark.asyncio
    async def test_mixed_answer_preserves_separate_provenance(self, session: AsyncSession) -> None:
        """Mixed answer keeps logistics graph and policy citations in distinct fields."""
        query_vector = _unit_vector(0)
        document = await _make_document(session, title="Procurement Policy")
        chunk = await _make_chunk(
            session,
            document,
            chunk_index=0,
            content="All procurement must follow the approved vendor list.",
            embedding=query_vector,
            page_number=2,
            section="Vendor Rules",
        )

        sentinel_graph = object()
        logistics_answer = _StubLogisticsAnswer(
            answer="Shipment SHP-001 is currently in transit.",
            graph=sentinel_graph,
        )
        logistics_evidence = _StubProcurementEvidence()
        llm = _StubLLMService("Shipment SHP-001 is in transit and must follow the approved vendor list.")
        embeddings = FixedQueryEmbeddingService(query_vector)

        result = await generate_grounded_mixed_answer(
            session,
            llm,  # type: ignore[arg-type]
            "What is the policy for this shipment?",
            embeddings,  # type: ignore[arg-type]
            logistics_answer,  # type: ignore[arg-type]
            logistics_evidence,  # type: ignore[arg-type]
        )

        assert isinstance(result, MixedAnswer)
        # Graph is the unmodified logistics graph — not merged with policy.
        assert result.graph is sentinel_graph
        # Citations trace to the policy chunk, not the logistics evidence.
        assert len(result.citations) == 1
        assert result.citations[0]["chunk_id"] == chunk.id
        assert result.citations[0]["source_title"] == "Procurement Policy"
        # Answer text is set.
        assert len(result.answer) > 0
