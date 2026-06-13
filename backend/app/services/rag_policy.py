"""Policy RAG query pipeline.

Stage: normalize a user's policy query and embed it once with the deployment's
active embedding profile (C38), then score profile-matched, ready chunk
candidates by cosine similarity against that query vector (C39). Fusion with
lexical retrieval is later (C40+).
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from app.services.llm import EmbeddingService

_WHITESPACE_RUN = re.compile(r"\s+")


class EmptyQueryError(Exception):
    """Raised when a policy query is blank after normalization."""


class PolicyChunkCandidate(TypedDict):
    """A retrievable policy chunk row, as read from `policy_chunks`/`policy_documents`.

    `status` is the document's lifecycle status (`policy_documents.status`).
    `embedding_provider`/`embedding_model`/`embedding_dimensions` are the
    document's embedding profile fields (`policy_documents.embedding_*`),
    joined onto the chunk row for profile-matched filtering. `embedding` is
    the chunk's stored 768-dim vector.
    """

    chunk_id: int
    document_id: int
    chunk_index: int
    page_number: int | None
    section: str | None
    text: str
    embedding: list[float]
    status: str
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int


class ScoredPolicyChunk(TypedDict):
    """A `PolicyChunkCandidate` paired with its cosine similarity score."""

    chunk: PolicyChunkCandidate
    score: float


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity of two equal-length vectors.

    Returns 0.0 if either vector has zero magnitude, to avoid division by zero
    for degenerate (all-zero) embeddings.
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have the same dimensionality.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def normalize_query(text: str) -> str:
    """NFC-normalize unicode and collapse all whitespace to single spaces."""
    normalized = unicodedata.normalize("NFC", text)
    return _WHITESPACE_RUN.sub(" ", normalized).strip()


class RAGPolicy:
    def __init__(self, embeddings: EmbeddingService) -> None:
        self._embeddings = embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Normalize a policy query and embed it with the active profile.

        Raises EmptyQueryError if the query is blank after normalization,
        without calling the embedding provider.
        """
        normalized = normalize_query(text)
        if not normalized:
            raise EmptyQueryError("Policy query must not be blank.")
        return await self._embeddings.embed_query(normalized)

    def fetch_vector_candidates(
        self,
        query_vector: list[float],
        candidates: list[PolicyChunkCandidate],
        top_k: int = 5,
    ) -> list[ScoredPolicyChunk]:
        """Score and rank ready, profile-matched chunk candidates by cosine similarity.

        Filters out any candidate whose document `status` is not `"ready"` or whose
        embedding profile does not match the active `EmbeddingService.profile` --
        mixing embeddings from different profiles would produce meaningless
        distances. Remaining candidates are scored against `query_vector` and
        returned sorted by descending similarity (ties broken by ascending
        `chunk_index` for deterministic ordering), truncated to `top_k`.
        """
        active_profile = self._embeddings.profile
        eligible = [
            c
            for c in candidates
            if c["status"] == "ready"
            and c["embedding_provider"] == active_profile.provider
            and c["embedding_model"] == active_profile.model
            and c["embedding_dimensions"] == active_profile.dimensions
        ]
        scored = [
            ScoredPolicyChunk(chunk=c, score=_cosine_similarity(query_vector, c["embedding"]))
            for c in eligible
        ]
        scored.sort(key=lambda s: (-s["score"], s["chunk"]["chunk_index"]))
        return scored[:top_k]

    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError
