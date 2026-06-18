"""Policy RAG query pipeline.

Stage: normalize a user's policy query and embed it once with the deployment's
active embedding profile (C38), then score profile-matched, ready chunk
candidates by cosine similarity against that query vector (C39), and retrieve
the top scoring chunks as cited evidence (C51). Grounded answer generation and
mixed logistics+policy answers are added in C54.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import PolicyChunk, PolicyDocument

if TYPE_CHECKING:
    from app.services.llm import ChatMessage, EmbeddingService, LLMService
    from app.services.rag_logistics import LogisticsAnswer, ProcurementEvidence

_WHITESPACE_RUN = re.compile(r"\s+")

# Candidates scoring below this cosine similarity are not reliable enough to
# cite as evidence and are discarded.
MIN_EVIDENCE_SCORE = 0.35


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


class PolicyEvidence(TypedDict):
    """A cited policy chunk, ready to surface to a caller.

    `source_title` is the owning `policy_documents.title`. `document_id` and
    `chunk_id` identify the stored row this citation traces back to --
    citations are sourced from `policy_chunks`, never invented.
    """

    source_title: str
    document_id: int
    chunk_id: int
    section: str | None
    page_number: int | None
    excerpt: str
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

    async def fetch_chunk_candidates(self, db: AsyncSession) -> list[PolicyChunkCandidate]:
        """Load all chunk candidates with embeddings, joined to their document.

        Only chunks that have a stored embedding are eligible -- a chunk
        without an embedding cannot be scored. Profile and status filtering
        happens in `fetch_vector_candidates`.
        """
        rows = (
            await db.execute(
                select(PolicyChunk, PolicyDocument)
                .join(PolicyDocument, PolicyChunk.document_id == PolicyDocument.id)
                .where(PolicyChunk.embedding.is_not(None))
            )
        ).all()

        candidates: list[PolicyChunkCandidate] = []
        for chunk, document in rows:
            candidates.append(
                PolicyChunkCandidate(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    text=chunk.content,
                    embedding=list(chunk.embedding),
                    status=document.status,
                    embedding_provider=document.embedding_provider,
                    embedding_model=document.embedding_model,
                    embedding_dimensions=document.embedding_dimensions,
                )
            )
        return candidates

    async def retrieve_evidence(self, db: AsyncSession, text: str) -> list[PolicyEvidence]:
        """Embed `text` once and return up to five cited, ready policy chunks.

        Candidates are filtered to the active embedding profile and `ready`
        document status (`fetch_vector_candidates`), then any candidate
        scoring below `MIN_EVIDENCE_SCORE` is discarded. The source title is
        looked up per result so callers can cite "Document Title, p. N,
        Section" without a second query.
        """
        query_vector = await self.embed_query(text)
        candidates = await self.fetch_chunk_candidates(db)
        scored = self.fetch_vector_candidates(query_vector, candidates, top_k=5)

        document_ids = {s["chunk"]["document_id"] for s in scored}
        titles: dict[int, str] = {}
        if document_ids:
            rows = (
                await db.execute(
                    select(PolicyDocument.id, PolicyDocument.title).where(
                        PolicyDocument.id.in_(document_ids)
                    )
                )
            ).all()
            titles = {document_id: title for document_id, title in rows}

        evidence: list[PolicyEvidence] = []
        for s in scored:
            if s["score"] < MIN_EVIDENCE_SCORE:
                continue
            chunk = s["chunk"]
            evidence.append(
                PolicyEvidence(
                    source_title=titles.get(chunk["document_id"], ""),
                    document_id=chunk["document_id"],
                    chunk_id=chunk["chunk_id"],
                    section=chunk["section"],
                    page_number=chunk["page_number"],
                    excerpt=chunk["text"],
                    score=s["score"],
                )
            )
        return evidence

    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError


# --- Grounded policy answer generation ----------------------------------------

_POLICY_SYSTEM_PROMPT = (
    "You are a policy assistant. Answer the user's question using only the "
    "policy excerpts provided below. Do not invent policy rules, leave "
    "entitlements, procedures, or document titles that are not present in the "
    "excerpts. If the excerpts do not contain the answer, say so plainly. "
    "Never mention databases, identifiers, or technical internals."
)


@dataclass(frozen=True)
class PolicyAnswer:
    """A grounded policy response: complete answer text and source citations.

    ``answer`` is either the LLM's generation (grounded only in
    ``PolicyEvidence``) or, on any ``LLMError``, a deterministic excerpt
    summary built directly from the evidence. ``citations`` traces every
    cited claim back to a stored ``policy_chunks`` row — nothing is invented.
    If evidence was absent, ``citations`` is empty and ``answer`` states that
    explicitly.
    """

    answer: str
    citations: list[PolicyEvidence]


@dataclass(frozen=True)
class MixedAnswer:
    """A grounded response combining logistics evidence and policy citations.

    ``answer`` contains the full composite response text. ``graph`` carries the
    unmodified logistics evidence graph (from ``LogisticsAnswer``). ``citations``
    carries the policy ``PolicyEvidence`` items — the two provenances are always
    kept separate so callers can distinguish logistics facts from policy rules.
    """

    answer: str
    graph: object  # ProcurementGraph — typed as object to avoid circular import
    citations: list[PolicyEvidence]


def _format_policy_excerpts(evidence: list[PolicyEvidence]) -> str:
    """Render ``evidence`` as a numbered plain-text block of policy excerpts.

    Each item includes its source title, optional section and page, and the
    chunk text. No content is invented: optional fields are omitted silently
    when absent rather than filled with guesses.
    """
    parts: list[str] = []
    for i, item in enumerate(evidence, start=1):
        location_parts: list[str] = [item["source_title"]]
        if item["section"]:
            location_parts.append(item["section"])
        if item["page_number"] is not None:
            location_parts.append(f"p. {item['page_number']}")
        location = ", ".join(location_parts)
        parts.append(f"[{i}] {location}\n{item['excerpt']}")
    return "\n\n".join(parts)


def _build_policy_prompt(question: str, evidence: list[PolicyEvidence]) -> "list[ChatMessage]":
    from app.services.llm import ChatMessage

    excerpt_block = _format_policy_excerpts(evidence)
    user_content = (
        f"Policy excerpts:\n{excerpt_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the excerpts above. Cite excerpt numbers where relevant."
    )
    return [
        ChatMessage(role="system", content=_POLICY_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]


def _excerpt_fallback(evidence: list[PolicyEvidence]) -> str:
    """Build a deterministic excerpt summary when the LLM is unavailable.

    Returns a plain concatenation of source labels and the first 200 characters
    of each excerpt — never invented content.
    """
    parts: list[str] = []
    for item in evidence:
        location_parts: list[str] = [item["source_title"]]
        if item["section"]:
            location_parts.append(item["section"])
        if item["page_number"] is not None:
            location_parts.append(f"p. {item['page_number']}")
        location = ", ".join(location_parts)
        excerpt = item["excerpt"][:200]
        parts.append(f"{location}: {excerpt}")
    return " | ".join(parts)


async def generate_grounded_policy_answer(
    db: AsyncSession,
    llm: "LLMService",
    text: str,
    embeddings: "EmbeddingService",
) -> PolicyAnswer:
    """Generate a grounded policy answer for ``text``.

    Retrieves up to five ``PolicyEvidence`` items via ``RAGPolicy.retrieve_evidence``,
    builds a provider-neutral prompt, and calls ``LLMService.chat()`` with
    ``stream=False``. On any ``LLMError`` (timeout, rate limit, provider
    unavailable) returns a deterministic excerpt summary instead. If no evidence
    is retrieved, returns an explicit "not found" answer with empty citations.
    """
    from app.services.llm import LLMError

    policy = RAGPolicy(embeddings=embeddings)
    try:
        evidence = await policy.retrieve_evidence(db, text)
    except EmptyQueryError:
        return PolicyAnswer(
            answer="The policy answer was not found in the available documents.",
            citations=[],
        )

    if not evidence:
        return PolicyAnswer(
            answer="The policy answer was not found in the available documents.",
            citations=[],
        )

    try:
        messages = _build_policy_prompt(text, evidence)
        chunks = await llm.chat(messages, stream=False)
        answer = "".join([chunk async for chunk in chunks])
    except LLMError:
        answer = _excerpt_fallback(evidence)

    return PolicyAnswer(answer=answer, citations=list(evidence))


async def generate_grounded_mixed_answer(
    db: AsyncSession,
    llm: "LLMService",
    text: str,
    embeddings: "EmbeddingService",
    logistics_answer: "LogisticsAnswer",
    logistics_evidence: "ProcurementEvidence",
) -> MixedAnswer:
    """Generate a grounded mixed answer combining logistics and policy evidence.

    Retrieves policy evidence via ``RAGPolicy.retrieve_evidence``, then builds a
    combined prompt that includes both the logistics answer and policy excerpts.
    The resulting ``MixedAnswer`` always preserves ``graph`` (from
    ``logistics_answer``) and ``citations`` (policy ``PolicyEvidence``) as
    distinct fields — logistics facts and policy rules are never merged into a
    single provenance. On any ``LLMError``, returns the logistics answer text
    with a policy excerpt summary appended, and empty citations when no policy
    evidence was found.
    """
    from app.services.llm import ChatMessage, LLMError

    policy = RAGPolicy(embeddings=embeddings)
    try:
        policy_evidence = await policy.retrieve_evidence(db, text)
    except EmptyQueryError:
        policy_evidence = []

    policy_section = (
        _format_policy_excerpts(policy_evidence)
        if policy_evidence
        else "No relevant policy excerpts found."
    )

    user_content = (
        f"Logistics answer:\n{logistics_answer.answer}\n\n"
        f"Policy excerpts:\n{policy_section}\n\n"
        f"Question: {text}\n\n"
        "Compose a combined answer using only the logistics answer and policy excerpts above. "
        "Clearly distinguish logistics facts from policy rules. "
        "Cite policy excerpt numbers where relevant."
    )
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=_POLICY_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]

    try:
        chunks = await llm.chat(messages, stream=False)
        answer = "".join([chunk async for chunk in chunks])
    except LLMError:
        policy_part = (
            _excerpt_fallback(policy_evidence)
            if policy_evidence
            else "No relevant policy excerpts found."
        )
        answer = f"{logistics_answer.answer} Policy context: {policy_part}"

    return MixedAnswer(
        answer=answer,
        graph=logistics_answer.graph,
        citations=list(policy_evidence),
    )
