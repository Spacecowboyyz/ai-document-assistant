from pathlib import Path

import fitz
import pytest

from app.core.pdf_parser import CHUNK_SIZE, parse_pdf


@pytest.mark.asyncio
async def test_parse_pdf_produces_chunks_with_metadata(sample_pdf_path: Path):
    documents = await parse_pdf(sample_pdf_path, sample_pdf_path.name)

    assert len(documents) >= 2
    for index, doc in enumerate(documents):
        assert doc.page_content.strip()
        assert doc.metadata["source_filename"] == sample_pdf_path.name
        assert "page_number" in doc.metadata
        assert doc.metadata["chunk_index"] == index
        assert len(doc.page_content) <= CHUNK_SIZE + 50


@pytest.mark.asyncio
async def test_parse_empty_pdf_raises(tmp_path: Path):
    empty_pdf = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(empty_pdf)
    doc.close()

    with pytest.raises(ValueError, match="no extractable text"):
        await parse_pdf(empty_pdf, "empty.pdf")


@pytest.mark.asyncio
async def test_parse_corrupt_pdf_raises(tmp_path: Path):
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a pdf file")

    with pytest.raises(ValueError, match="Unable to open PDF"):
        await parse_pdf(corrupt, "corrupt.pdf")
