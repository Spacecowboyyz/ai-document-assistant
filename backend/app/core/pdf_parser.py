from __future__ import annotations

import asyncio
from pathlib import Path

import fitz
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _extract_and_split(file_path: Path, source_filename: str) -> list[Document]:
    documents: list[Document] = []
    try:
        pdf = fitz.open(file_path)
    except Exception as exc:
        raise ValueError(f"Unable to open PDF: {exc}") from exc

    try:
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            text = page.get_text().strip()
            if not text:
                continue
            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "page_number": page_index + 1,
                        "source_filename": source_filename,
                    },
                )
            )
    finally:
        pdf.close()

    if not documents:
        raise ValueError("PDF contains no extractable text")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )
    chunks = splitter.split_documents(documents)

    result: list[Document] = []
    for chunk_index, chunk in enumerate(chunks):
        metadata = dict(chunk.metadata)
        metadata["chunk_index"] = chunk_index
        result.append(Document(page_content=chunk.page_content, metadata=metadata))
    return result


async def parse_pdf(file_path: Path, source_filename: str) -> list[Document]:
    return await asyncio.to_thread(_extract_and_split, file_path, source_filename)
