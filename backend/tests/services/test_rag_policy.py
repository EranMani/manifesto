"""Tests for backend/app/services/rag_policy.py — query normalization and embedding."""

import pytest

from app.services.rag_policy import EmptyQueryError, RAGPolicy


class FakeEmbeddingService:
    """Deterministic embedding test double; tracks calls, no provider SDKs involved."""

    def __init__(self, dimensions: int = 8) -> None:
        self._dimensions = dimensions
        self.embed_documents_calls: list[list[str]] = []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embed_documents_calls.append(list(texts))
        return [[float(len(t) % 7) + 0.1 * i for i in range(self._dimensions)] for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0]


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
