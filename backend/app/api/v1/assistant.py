from __future__ import annotations

import functools
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.assistant import (
    ActionBadgeSchema,
    AssistantQueryRequest,
    AssistantQueryResponse,
    CitationSchema,
    GraphEdgeSchema,
    GraphNodeSchema,
    GraphSchema,
)
from app.services.assistant import (
    AssistantAnswer,
    DeniedAnswer,
    answer_question,
)
from app.services.badge_engine import select_badges
from app.services.llm import EmbeddingService, LLMError, LLMService
from app.services.rag_logistics import LogisticsAnswer
from app.services.rag_policy import MixedAnswer, PolicyAnswer

logger = logging.getLogger(__name__)

router = APIRouter()


@functools.lru_cache(maxsize=1)
def _build_embedding_service() -> EmbeddingService:
    return EmbeddingService(
        provider=settings.EMBEDDING_PROVIDER,
        model=settings.EMBEDDING_MODEL or "",
        dimensions=settings.EMBEDDING_DIMENSIONS,
        openai_api_key=settings.OPENAI_API_KEY,
        ollama_base_url=settings.OLLAMA_BASE_URL,
    )


def _build_llm_service() -> LLMService:
    if settings.OPENAI_API_KEY:
        return LLMService(
            "openai",
            openai_api_key=settings.OPENAI_API_KEY,
            openai_chat_model=settings.OPENAI_CHAT_MODEL,
        )
    return LLMService(
        "ollama",
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_chat_model=settings.OLLAMA_CHAT_MODEL,
    )


def _graph_from_logistics(answer: LogisticsAnswer) -> GraphSchema:
    return GraphSchema(
        nodes=[
            GraphNodeSchema(
                id=n.id, type=n.type, label=n.label,
                status=n.status, status_category=n.status_category,
            )
            for n in answer.graph.nodes
        ],
        edges=[
            GraphEdgeSchema(
                source=e.source, target=e.target, relationship=e.relationship
            )
            for e in answer.graph.edges
        ],
        highlighted_path=list(answer.graph.highlighted_path),
    )


def _citations_from_policy(evidence: list) -> list[CitationSchema]:
    return [
        CitationSchema(
            source_title=e["source_title"],
            document_id=e["document_id"],
            chunk_id=e["chunk_id"],
            section=e.get("section"),
            page_number=e.get("page_number"),
            excerpt=e["excerpt"],
            score=e["score"],
        )
        for e in evidence
    ]


def _extract_badge_context(result: AssistantAnswer) -> tuple[str, str | None]:
    graph = None
    if isinstance(result, LogisticsAnswer):
        graph = result.graph
    elif isinstance(result, MixedAnswer) and hasattr(result.graph, "nodes"):
        graph = result.graph

    if graph is None:
        return "", None

    shipment_status = ""
    latest_event_type = None
    for node in graph.nodes:
        if node.type == "shipment" and hasattr(node, "status") and node.status:
            shipment_status = node.status
    for node in graph.nodes:
        if node.type == "event":
            latest_event_type = node.label

    return shipment_status, latest_event_type


def _to_response(result: AssistantAnswer, role: str) -> AssistantQueryResponse:
    shipment_status, latest_event_type = _extract_badge_context(result)
    badges = select_badges(shipment_status, latest_event_type, role)
    badge_schemas = [ActionBadgeSchema(label=b.label, prompt=b.prompt) for b in badges]

    if isinstance(result, DeniedAnswer):
        return AssistantQueryResponse(intent="denied", answer=result.message)

    if isinstance(result, PolicyAnswer):
        return AssistantQueryResponse(
            intent="policy",
            answer=result.answer,
            citations=_citations_from_policy(result.citations),
            action_badges=badge_schemas,
        )

    if isinstance(result, LogisticsAnswer):
        return AssistantQueryResponse(
            intent="logistics",
            answer=result.answer,
            graph=_graph_from_logistics(result),
            suggested_questions=list(result.follow_ups),
            action_badges=badge_schemas,
        )

    if isinstance(result, MixedAnswer):
        graph = None
        if hasattr(result.graph, "nodes"):
            graph = GraphSchema(
                nodes=[
                    GraphNodeSchema(
                        id=n.id, type=n.type, label=n.label,
                        status=getattr(n, "status", None),
                        status_category=getattr(n, "status_category", None),
                    )
                    for n in result.graph.nodes
                ],
                edges=[
                    GraphEdgeSchema(
                        source=e.source,
                        target=e.target,
                        relationship=e.relationship,
                    )
                    for e in result.graph.edges
                ],
                highlighted_path=list(result.graph.highlighted_path),
            )
        return AssistantQueryResponse(
            intent="mixed",
            answer=result.answer,
            graph=graph,
            citations=_citations_from_policy(result.citations),
            action_badges=badge_schemas,
        )

    return AssistantQueryResponse(intent="unknown", answer="Unexpected response type.")


@router.post("/query", response_model=AssistantQueryResponse)
async def query_assistant(
    body: AssistantQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssistantQueryResponse:
    llm = _build_llm_service()
    embeddings = _build_embedding_service()
    try:
        result = await answer_question(
            user_role=current_user.role,
            message=body.message,
            db=db,
            llm=llm,
            embeddings=embeddings,
        )
    except LLMError:
        logger.exception("LLM provider error during assistant query")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service is temporarily unavailable. Please try again.",
        )
    except Exception:
        logger.exception("Unexpected error during assistant query")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Something went wrong processing your question. Please try again.",
        )
    try:
        return _to_response(result, role=current_user.role)
    except Exception:
        logger.exception("Error converting assistant response")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Something went wrong processing your question. Please try again.",
        )
