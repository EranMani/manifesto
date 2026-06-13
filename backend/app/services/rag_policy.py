"""Policy RAG query pipeline.

Stage: normalize a user's policy query and embed it once with the deployment's
active embedding profile. Retrieval against the embedding is C39-C40.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.llm import EmbeddingService

_WHITESPACE_RUN = re.compile(r"\s+")


class EmptyQueryError(Exception):
    """Raised when a policy query is blank after normalization."""


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

    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError
