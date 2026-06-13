"""Tests for backend/app/services/rag_policy.py — query normalization, embedding,
and vector candidate retrieval."""

import pytest

from app.services.llm import EmbeddingProfile
from app.services.rag_policy import EmptyQueryError, PolicyChunkCandidate, RAGPolicy

ACTIVE_PROFILE = EmbeddingProfile(provider="ollama", model="nomic-embed-text", dimensions=768)


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
