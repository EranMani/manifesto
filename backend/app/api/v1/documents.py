"""Manager/admin document ingestion API.

Routes are a thin shell around the frozen ingestion contract in
``app.services.ingestion``. No parsing or embedding logic lives here:
the route validates the upload, creates the ``policy_documents`` row, and
delegates to ``ingest_document`` which owns the processing -> ready|failed
transition and never raises to the caller.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import require_role
from app.models.policy import PolicyDocument
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentRead, DocumentUploadResponse
from app.services.ingestion import IngestionError, ingest_document
from app.services.llm import EmbeddingService, LLMError

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Validation configuration
# ---------------------------------------------------------------------------

_ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

_ALLOWED_EXTENSIONS = set(_ALLOWED_CONTENT_TYPES.values())

# Magic-number signatures used to confirm the declared content type matches the
# actual file bytes. Plain text / markdown have no reliable signature and are
# validated only by attempting decode during extraction.
_PDF_SIGNATURE = b"%PDF-"
_DOCX_SIGNATURE = b"PK\x03\x04"  # OOXML/zip container

_READ_CHUNK_SIZE = 1024 * 1024  # 1 MiB

_TITLE_MAX_LENGTH = 255

_UPLOAD_ROLES = ("manager", "admin")


# ---------------------------------------------------------------------------
# Embedding service dependency
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _build_embedding_service() -> EmbeddingService:
    """Construct the deployment-wide embedding service from settings.

    Cached as a singleton: the embedding profile is fixed at startup and
    EmbeddingService manages a pooled async HTTP client.
    """
    return EmbeddingService(
        provider=settings.EMBEDDING_PROVIDER,
        model=settings.EMBEDDING_MODEL or "",
        dimensions=settings.EMBEDDING_DIMENSIONS,
        openai_api_key=settings.OPENAI_API_KEY,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        connect_timeout=settings.LLM_CONNECT_TIMEOUT,
        read_timeout=settings.LLM_READ_TIMEOUT,
        total_timeout=settings.LLM_TOTAL_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )


def get_embedding_service() -> EmbeddingService:
    return _build_embedding_service()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(filename: str | None) -> str | None:
    """Strip any path components and unsafe characters from a client filename.

    Never used as a filesystem path -- this only produces a display-safe value
    for storage in ``original_filename``.
    """
    if not filename:
        return None
    # Drop any directory components from either path style.
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name:
        return None
    name = _FILENAME_SAFE.sub("_", name)
    return name[:255] or None


def _extension_for(filename: str | None) -> str | None:
    if not filename:
        return None
    idx = filename.rfind(".")
    if idx == -1:
        return None
    return filename[idx:].lower()


def _detect_signature_mismatch(content_type: str, head: bytes) -> bool:
    """Return True if the file signature does not match the declared content type."""
    if content_type == "application/pdf":
        return not head.startswith(_PDF_SIGNATURE)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return not head.startswith(_DOCX_SIGNATURE)
    # text/plain and text/markdown have no fixed signature.
    return False


def _encode_cursor(uploaded_at, document_id: str) -> str:
    raw = f"{uploaded_at.isoformat()}|{document_id}".encode("utf-8")
    return urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        raw = urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        uploaded_at_str, document_id = raw.split("|", 1)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor"
        ) from exc
    return uploaded_at_str, document_id


# Best-effort mapping from ingestion's sanitized error_message strings (see
# app.services.ingestion._sanitize_error and the IngestionError subclasses) to a
# stable, non-leaking failure code. This couples to the exact message text used
# by ingestion.py; if Nova adds a structured error code to IngestResult/
# policy_documents, this mapping should be replaced with a direct lookup.
_FAILURE_CODE_BY_MESSAGE: dict[str, "DocumentFailureCode"] = {
    "PDF is encrypted and cannot be ingested.": "encrypted_document",
    "DOCX is encrypted and cannot be ingested.": "encrypted_document",
    "Could not open PDF document.": "corrupt_document",
    "Could not open DOCX document.": "corrupt_document",
    "PDF exceeds the maximum supported page count.": "corrupt_document",
    "PDF exceeds the maximum supported structure size.": "corrupt_document",
    "DOCX exceeds the maximum supported structure size.": "corrupt_document",
    "Document exceeds the maximum supported size.": "corrupt_document",
    "Document exceeds the maximum supported structure size.": "corrupt_document",
    "PDF contains only images; OCR is not supported.": "image_only_document",
    "PDF contains no extractable text.": "empty_document",
    "DOCX contains no extractable text.": "empty_document",
    "Document contains no extractable text.": "empty_document",
    "Uploaded file is empty.": "empty_document",
    "Document is not valid UTF-8 text.": "invalid_encoding",
}


def _failure_code_for(doc: PolicyDocument) -> "DocumentFailureCode | None":
    if doc.status != "failed":
        return None
    message = doc.error_message or ""
    if message.startswith("Unsupported content type:"):
        return "unsupported_content_type"
    return _FAILURE_CODE_BY_MESSAGE.get(message, "internal_error")


def _document_payload(doc: PolicyDocument) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "original_filename": doc.original_filename,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "uploaded_by": doc.uploaded_by,
        "embedding_provider": doc.embedding_provider,
        "embedding_model": doc.embedding_model,
        "embedding_dimensions": doc.embedding_dimensions,
        "uploaded_at": doc.uploaded_at,
        "updated_at": doc.updated_at,
        "failure_code": _failure_code_for(doc),
    }


def _to_read_model(doc: PolicyDocument) -> DocumentRead:
    return DocumentRead.model_validate(_document_payload(doc))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DocumentUploadResponse)
async def upload_document(
    response: Response,
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(require_role(*_UPLOAD_ROLES)),
    db: AsyncSession = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service),
) -> DocumentUploadResponse | object:
    trimmed_title = title.strip()
    if not trimmed_title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="title must not be blank")
    if len(trimmed_title) > _TITLE_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"title must be at most {_TITLE_MAX_LENGTH} characters",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported content type",
        )

    safe_filename = _sanitize_filename(file.filename)
    extension = _extension_for(safe_filename)
    if extension is None or extension not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file extension",
        )
    if extension != _ALLOWED_CONTENT_TYPES[content_type]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File extension does not match content type",
        )

    # Read the body in bounded chunks; never trust Content-Length.
    max_bytes = settings.MAX_DOCUMENT_UPLOAD_BYTES
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds the maximum upload size",
            )
        chunks.append(chunk)

    file_bytes = b"".join(chunks)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded file is empty")

    if _detect_signature_mismatch(content_type, file_bytes[:8]):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File signature does not match content type",
        )

    sha256 = hashlib.sha256(file_bytes).hexdigest()
    profile = embeddings.profile

    # Idempotency: an existing ready document with the same checksum and
    # embedding profile is returned as-is without re-ingesting.
    existing = await db.execute(
        select(PolicyDocument).where(
            PolicyDocument.sha256 == sha256,
            PolicyDocument.embedding_provider == profile.provider,
            PolicyDocument.embedding_model == profile.model,
            PolicyDocument.embedding_dimensions == profile.dimensions,
            PolicyDocument.status == "ready",
        )
    )
    existing_doc = existing.scalars().first()
    if existing_doc is not None:
        response.status_code = status.HTTP_200_OK
        return DocumentUploadResponse.model_validate(_document_payload(existing_doc))

    document = PolicyDocument(
        title=trimmed_title,
        original_filename=safe_filename,
        content_type=content_type,
        byte_size=total,
        sha256=sha256,
        status="processing",
        uploaded_by=current_user.id,
        embedding_provider=profile.provider,
        embedding_model=profile.model,
        embedding_dimensions=profile.dimensions,
    )
    db.add(document)
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise

    document_id = document.id
    await db.commit()

    try:
        await ingest_document(
            document_id=document_id,
            file_bytes=file_bytes,
            filename=safe_filename or "document",
            content_type=content_type,
            db=db,
            embeddings=embeddings,
        )
    except (IngestionError, LLMError) as exc:
        logger.warning(
            "document ingestion failed",
            extra={"document_id": document_id, "error_type": type(exc).__name__},
        )

    refreshed = await db.execute(select(PolicyDocument).where(PolicyDocument.id == document_id))
    document = refreshed.scalars().first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document ingestion is temporarily unavailable"
        )

    return DocumentUploadResponse.model_validate(_document_payload(document))


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role(*_UPLOAD_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    stmt = select(PolicyDocument).order_by(PolicyDocument.uploaded_at.desc(), PolicyDocument.id.desc())

    if cursor:
        uploaded_at_str, doc_id = _decode_cursor(cursor)
        try:
            import datetime as _dt

            uploaded_at = _dt.datetime.fromisoformat(uploaded_at_str)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc

        stmt = stmt.where(
            (PolicyDocument.uploaded_at < uploaded_at)
            | ((PolicyDocument.uploaded_at == uploaded_at) & (PolicyDocument.id < doc_id))
        )

    stmt = stmt.limit(limit + 1)
    result = await db.execute(stmt)
    documents = list(result.scalars().all())

    next_cursor: str | None = None
    if len(documents) > limit:
        documents = documents[:limit]
        last = documents[-1]
        next_cursor = _encode_cursor(last.uploaded_at, last.id)

    return DocumentListResponse(items=[_to_read_model(doc) for doc in documents], next_cursor=next_cursor)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: str,
    current_user: User = Depends(require_role(*_UPLOAD_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    result = await db.execute(select(PolicyDocument).where(PolicyDocument.id == document_id))
    document = result.scalars().first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return _to_read_model(document)
