from __future__ import annotations

import uuid
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.core.pdf_parser import parse_pdf
from app.core.provider_factory import get_embedding_provider
from app.core.providers import OllamaAvailability
from app.core.vector_store import ChromaVectorStore
from app.models.document_meta import DocumentMeta
from app.schemas.document import DeleteResponse, DocumentInfo, UploadResponse


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        ollama: OllamaAvailability,
        db: Session,
    ) -> None:
        self._settings = settings
        self._ollama = ollama
        self._db = db
        embedding = get_embedding_provider(settings, ollama)
        self._vector_store = ChromaVectorStore(settings, embedding)

    async def ingest_upload(self, file: UploadFile, user_id: UUID) -> UploadResponse:
        await self._ollama.require_available()

        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported",
            )

        doc_id = str(uuid.uuid4())
        dest_path = self._settings.uploads_path / f"{doc_id}.pdf"
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        size = 0
        try:
            async with aiofiles.open(dest_path, "wb") as out_file:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self._settings.max_upload_size_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=(
                                f"File exceeds maximum size of "
                                f"{self._settings.max_upload_size_mb}MB"
                            ),
                        )
                    await out_file.write(chunk)
        except HTTPException:
            if dest_path.exists():
                dest_path.unlink()
            raise
        except Exception as exc:
            if dest_path.exists():
                dest_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store uploaded file: {exc}",
            ) from exc

        try:
            documents = await parse_pdf(dest_path, file.filename)
            await self._vector_store.add_documents(doc_id, documents)
            chunk_count = len(documents)
        except ValueError as exc:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except HTTPException:
            dest_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            dest_path.unlink(missing_ok=True)
            self._vector_store.delete_collection(doc_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to index document: {exc}",
            ) from exc

        meta = DocumentMeta(
            doc_id=doc_id,
            user_id=user_id,
            filename=file.filename,
            chunk_count=chunk_count,
        )
        self._db.add(meta)
        self._db.commit()

        return UploadResponse(
            doc_id=doc_id,
            filename=file.filename,
            chunk_count=chunk_count,
        )

    async def list_documents(self, user_id: UUID) -> list[DocumentInfo]:
        rows = self._db.scalars(
            select(DocumentMeta)
            .where(DocumentMeta.user_id == user_id)
            .order_by(DocumentMeta.created_at.desc())
        ).all()
        results: list[DocumentInfo] = []
        for row in rows:
            pdf_path = self._settings.uploads_path / f"{row.doc_id}.pdf"
            if not pdf_path.exists():
                continue
            results.append(
                DocumentInfo(
                    doc_id=row.doc_id,
                    filename=row.filename,
                    chunk_count=row.chunk_count,
                    created_at=row.created_at,
                )
            )
        return results

    def get_owned_document(self, doc_id: str, user_id: UUID) -> DocumentMeta:
        meta = self._db.scalar(
            select(DocumentMeta).where(DocumentMeta.doc_id == doc_id)
        )
        if meta is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Document not found or access denied",
            )
        if meta.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )
        return meta

    async def delete_document(self, doc_id: str, user_id: UUID) -> DeleteResponse:
        meta = self.get_owned_document(doc_id, user_id)
        pdf_path = self._settings.uploads_path / f"{doc_id}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()
        self._vector_store.delete_collection(doc_id)
        self._db.delete(meta)
        self._db.commit()
        return DeleteResponse(doc_id=doc_id, deleted=True)
