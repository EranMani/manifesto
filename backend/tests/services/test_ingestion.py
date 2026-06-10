"""Tests for document ingestion: extraction, chunking, and orchestration."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ingestion import (
    Chunk,
    CorruptDocumentError,
    EmptyDocumentError,
    EncryptedDocumentError,
    ExtractedBlock,
    ImageOnlyDocumentError,
    IngestionError,
    InvalidEncodingError,
    UnsupportedContentTypeError,
    chunk_blocks,
    extract_document,
    ingest_document,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"


def _load(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


# ---------------------------------------------------------------------------
# extract_document — PDF
# ---------------------------------------------------------------------------


class TestExtractPdf:
    def test_extracts_pages_and_text(self) -> None:
        doc = extract_document(_load("sample.pdf"), "application/pdf")
        assert doc.blocks
        page_numbers = {b.page_number for b in doc.blocks}
        assert page_numbers == {1, 2}

    def test_extracts_unicode(self) -> None:
        doc = extract_document(_load("sample.pdf"), "application/pdf")
        joined = " ".join(b.text for b in doc.blocks)
        assert "café" in joined or "中文" in joined

    def test_encrypted_pdf_raises(self) -> None:
        with pytest.raises(EncryptedDocumentError):
            extract_document(_load("encrypted.pdf"), "application/pdf")

    def test_image_only_pdf_raises(self) -> None:
        with pytest.raises(ImageOnlyDocumentError):
            extract_document(_load("image_only.pdf"), "application/pdf")

    def test_corrupt_pdf_raises(self) -> None:
        with pytest.raises(CorruptDocumentError):
            extract_document(b"not a pdf at all", "application/pdf")


# ---------------------------------------------------------------------------
# extract_document — DOCX
# ---------------------------------------------------------------------------


class TestExtractDocx:
    def test_extracts_headings_paragraphs_and_tables(self) -> None:
        doc = extract_document(_load("sample.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        texts = [b.text for b in doc.blocks]
        assert any("Sample Policy" in t for t in texts)
        assert any("Header A | Header B" in t for t in texts)

    def test_assigns_section_from_headings(self) -> None:
        doc = extract_document(_load("sample.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        sections = {b.section for b in doc.blocks}
        assert "Sample Policy" in sections or "Details Section" in sections

    def test_extracts_unicode(self) -> None:
        doc = extract_document(_load("sample.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        joined = " ".join(b.text for b in doc.blocks)
        assert "café" in joined and "中文" in joined

    def test_encrypted_docx_raises_encrypted_not_corrupt(self) -> None:
        """OLE-CFB encrypted OOXML must map to EncryptedDocumentError, not CorruptDocumentError."""
        with pytest.raises(EncryptedDocumentError):
            extract_document(_load("encrypted.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_corrupt_docx_raises(self) -> None:
        with pytest.raises(CorruptDocumentError):
            extract_document(_load("corrupt.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_empty_docx_raises(self) -> None:
        import docx
        import io

        document = docx.Document()
        buf = io.BytesIO()
        document.save(buf)
        with pytest.raises(EmptyDocumentError):
            extract_document(buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


# ---------------------------------------------------------------------------
# extract_document — TXT / MD
# ---------------------------------------------------------------------------


class TestExtractPlainText:
    def test_txt_extracts_paragraphs_and_unicode(self) -> None:
        doc = extract_document(_load("sample.txt"), "text/plain")
        joined = " ".join(b.text for b in doc.blocks)
        assert "café" in joined
        assert len(doc.blocks) >= 2

    def test_md_extracts_heading_as_section(self) -> None:
        doc = extract_document(_load("sample.md"), "text/markdown")
        sections = {b.section for b in doc.blocks}
        assert "Introduction" in sections
        assert "Section Two" in sections

    def test_empty_txt_raises(self) -> None:
        with pytest.raises(EmptyDocumentError):
            extract_document(b"   \n\n  ", "text/plain")

    def test_invalid_utf8_raises(self) -> None:
        with pytest.raises(InvalidEncodingError):
            extract_document(b"\xff\xfe\x00invalid", "text/plain")

    def test_empty_bytes_raises(self) -> None:
        with pytest.raises(EmptyDocumentError):
            extract_document(b"", "text/plain")


# ---------------------------------------------------------------------------
# extract_document — dispatch
# ---------------------------------------------------------------------------


class TestExtractDispatch:
    def test_unsupported_content_type_raises(self) -> None:
        with pytest.raises(UnsupportedContentTypeError):
            extract_document(b"data", "application/zip")


# ---------------------------------------------------------------------------
# chunk_blocks
# ---------------------------------------------------------------------------


class TestChunkBlocks:
    def test_empty_blocks_returns_empty(self) -> None:
        assert chunk_blocks([]) == []

    def test_sequential_indices(self) -> None:
        blocks = [ExtractedBlock(text=f"Paragraph {i} " * 50, page_number=1, section=None) for i in range(5)]
        chunks = chunk_blocks(blocks)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_hard_cap_enforced(self) -> None:
        # One huge block far exceeding the hard cap must be split.
        big_text = "word " * 5000
        blocks = [ExtractedBlock(text=big_text, page_number=1, section=None)]
        chunks = chunk_blocks(blocks)
        assert len(chunks) > 1
        for c in chunks:
            assert c.token_count <= 600

    def test_deterministic(self) -> None:
        blocks = [ExtractedBlock(text=f"Sentence number {i}. " * 30, page_number=1, section="A") for i in range(8)]
        chunks1 = chunk_blocks(blocks)
        chunks2 = chunk_blocks(blocks)
        assert [(c.chunk_index, c.content, c.token_count) for c in chunks1] == [
            (c.chunk_index, c.content, c.token_count) for c in chunks2
        ]

    def test_section_boundary_starts_new_chunk(self) -> None:
        blocks = [
            ExtractedBlock(text="Content in section A. " * 5, page_number=1, section="A"),
            ExtractedBlock(text="Content in section B. " * 5, page_number=1, section="B"),
        ]
        chunks = chunk_blocks(blocks)
        sections = [c.section for c in chunks]
        assert "A" in sections
        assert "B" in sections
        # Each chunk's content should not mix both sections' text.
        for c in chunks:
            if c.section == "A":
                assert "section B" not in c.content
            if c.section == "B":
                assert "section A" not in c.content

    def test_overlap_within_same_section(self) -> None:
        # Many small blocks (each well under the 60-token overlap budget) so the
        # overlap tail can span whole blocks once a flush occurs.
        blocks = [
            ExtractedBlock(text=f"Block {i} contains some filler words.", page_number=1, section="A")
            for i in range(80)
        ]
        chunks = chunk_blocks(blocks)
        assert len(chunks) >= 2
        # The first block of chunk 1's content should also appear in chunk 0 (overlap tail).
        first_line_of_next = chunks[1].content.split("\n\n")[0]
        assert first_line_of_next in chunks[0].content

    def test_metadata_preserved(self) -> None:
        blocks = [ExtractedBlock(text="Some content here.", page_number=3, section="My Section")]
        chunks = chunk_blocks(blocks)
        assert chunks[0].page_number == 3
        assert chunks[0].section == "My Section"


# ---------------------------------------------------------------------------
# ingest_document — orchestration
# ---------------------------------------------------------------------------


class FakeProfile:
    def __init__(self, provider: str = "ollama", model: str = "fake-embed", dimensions: int = 8) -> None:
        self.provider = provider
        self.model = model
        self.dimensions = dimensions


class FakeEmbeddingService:
    """Deterministic embedding test double; no real provider SDKs involved."""

    def __init__(self, dimensions: int = 8, profile: FakeProfile | None = None) -> None:
        self._dimensions = dimensions
        self._profile = profile or FakeProfile(dimensions=dimensions)

    @property
    def profile(self) -> FakeProfile:
        return self._profile

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7) + 0.1 * i for i in range(self._dimensions)] for t in texts]


def _make_db_mock(rowcount: int = 1) -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(rowcount=rowcount))
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
class TestIngestDocument:
    async def test_success_path_publishes_chunks(self) -> None:
        db = _make_db_mock(rowcount=1)
        embeddings = FakeEmbeddingService(dimensions=8)

        result = await ingest_document(
            document_id="doc-1",
            file_bytes=_load("sample.txt"),
            filename="sample.txt",
            content_type="text/plain",
            db=db,
            embeddings=embeddings,
        )

        assert result.status == "ready"
        assert result.chunk_count > 0
        assert result.error_message is None
        db.commit.assert_awaited()
        db.rollback.assert_not_awaited()
        # db.add called once per chunk.
        assert db.add.call_count == result.chunk_count

    async def test_empty_document_marks_failed_with_no_partial_chunks(self) -> None:
        db = _make_db_mock(rowcount=1)
        embeddings = FakeEmbeddingService(dimensions=8)

        result = await ingest_document(
            document_id="doc-2",
            file_bytes=b"   ",
            filename="empty.txt",
            content_type="text/plain",
            db=db,
            embeddings=embeddings,
        )

        assert result.status == "failed"
        assert result.chunk_count == 0
        assert result.error_message
        db.add.assert_not_called()
        db.rollback.assert_awaited()
        db.commit.assert_awaited()

    async def test_embedding_dimension_count_mismatch_rolls_back(self) -> None:
        db = _make_db_mock(rowcount=1)

        class MismatchedEmbeddingService(FakeEmbeddingService):
            async def embed_documents(self, texts: list[str]) -> list[list[float]]:
                # Return one fewer vector than chunks to trigger the mismatch guard.
                vectors = await super().embed_documents(texts)
                return vectors[:-1] if len(vectors) > 1 else []

        embeddings = MismatchedEmbeddingService(dimensions=8)

        result = await ingest_document(
            document_id="doc-3",
            file_bytes=_load("sample.txt"),
            filename="sample.txt",
            content_type="text/plain",
            db=db,
            embeddings=embeddings,
        )

        assert result.status == "failed"
        assert result.chunk_count == 0
        db.add.assert_not_called()
        db.rollback.assert_awaited()

    async def test_unsupported_content_type_marks_failed(self) -> None:
        db = _make_db_mock(rowcount=1)
        embeddings = FakeEmbeddingService(dimensions=8)

        result = await ingest_document(
            document_id="doc-4",
            file_bytes=b"some bytes",
            filename="file.zip",
            content_type="application/zip",
            db=db,
            embeddings=embeddings,
        )

        assert result.status == "failed"
        assert "Unsupported content type" in result.error_message

    async def test_document_row_not_found_marks_failed(self) -> None:
        # First call (advisory lock) ok, then publish UPDATE returns rowcount=0.
        db = MagicMock()
        responses = iter([
            MagicMock(rowcount=0),  # SELECT pg_advisory_xact_lock (publish path)
            MagicMock(rowcount=0),  # delete chunks
            MagicMock(rowcount=0),  # UPDATE policy_documents -> rowcount 0 triggers failure
            MagicMock(rowcount=0),  # advisory lock (failure path)
            MagicMock(rowcount=0),  # delete chunks (failure path)
            MagicMock(rowcount=0),  # UPDATE status='failed'
        ])
        db.execute = AsyncMock(side_effect=lambda *a, **k: next(responses))
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()

        embeddings = FakeEmbeddingService(dimensions=8)

        result = await ingest_document(
            document_id="doc-5",
            file_bytes=_load("sample.txt"),
            filename="sample.txt",
            content_type="text/plain",
            db=db,
            embeddings=embeddings,
        )

        assert result.status == "failed"
        assert result.error_message == "Document row not found during publish."
        db.rollback.assert_awaited()

    async def test_advisory_lock_acquired(self) -> None:
        db = _make_db_mock(rowcount=1)
        embeddings = FakeEmbeddingService(dimensions=8)

        await ingest_document(
            document_id="doc-lock",
            file_bytes=_load("sample.txt"),
            filename="sample.txt",
            content_type="text/plain",
            db=db,
            embeddings=embeddings,
        )

        lock_calls = [
            call for call in db.execute.await_args_list
            if "pg_advisory_xact_lock" in str(call.args[0])
        ]
        assert lock_calls

    async def test_idempotent_retry_produces_identical_chunks(self) -> None:
        """Calling ingest_document twice with the same input replaces, not duplicates."""
        embeddings = FakeEmbeddingService(dimensions=8)

        added_chunks_run1: list = []
        added_chunks_run2: list = []

        def make_db(sink: list) -> MagicMock:
            db = MagicMock()
            db.execute = AsyncMock(return_value=MagicMock(rowcount=1))
            db.add = MagicMock(side_effect=lambda obj: sink.append(obj))
            db.commit = AsyncMock()
            db.rollback = AsyncMock()
            return db

        db1 = make_db(added_chunks_run1)
        db2 = make_db(added_chunks_run2)

        result1 = await ingest_document(
            document_id="doc-retry",
            file_bytes=_load("sample.md"),
            filename="sample.md",
            content_type="text/markdown",
            db=db1,
            embeddings=embeddings,
        )
        result2 = await ingest_document(
            document_id="doc-retry",
            file_bytes=_load("sample.md"),
            filename="sample.md",
            content_type="text/markdown",
            db=db2,
            embeddings=embeddings,
        )

        assert result1.status == result2.status == "ready"
        assert result1.chunk_count == result2.chunk_count

        contents1 = [(c.chunk_index, c.content) for c in added_chunks_run1]
        contents2 = [(c.chunk_index, c.content) for c in added_chunks_run2]
        assert contents1 == contents2

        # Both runs must have issued a delete for existing chunks before re-adding.
        delete_calls_1 = [
            call for call in db1.execute.await_args_list if "DELETE" in str(call.args[0]).upper() or "policy_chunks" in str(call.args[0]).lower()
        ]
        assert delete_calls_1


# ---------------------------------------------------------------------------
# Optional DB integration test (requires a live database)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("MANIFESTO_DB_INTEGRATION_TESTS"),
    reason="Set MANIFESTO_DB_INTEGRATION_TESTS=1 to run against a live database.",
)
@pytest.mark.asyncio
class TestIngestDocumentIntegration:
    async def test_ingest_against_real_database(self) -> None:
        pytest.skip("Integration harness not wired up in this environment.")
