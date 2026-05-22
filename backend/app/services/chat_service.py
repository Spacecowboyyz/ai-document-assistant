from __future__ import annotations

import json
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.core.memory import MemoryManager
from app.core.provider_factory import get_chat_provider, get_embedding_provider
from app.core.providers import OllamaAvailability
from app.core.rag_pipeline import RAGPipeline
from app.core.vector_store import ChromaVectorStore
from app.schemas.chat import ChatRequest, SourceDocument
from app.services.document_service import DocumentService


class ChatService:
    def __init__(
        self,
        settings: Settings,
        ollama: OllamaAvailability,
        memory_manager: MemoryManager,
        db: Session,
    ) -> None:
        self._settings = settings
        self._ollama = ollama
        self._memory_manager = memory_manager
        self._db = db
        embedding = get_embedding_provider(settings, ollama)
        self._vector_store = ChromaVectorStore(settings, embedding)
        self._chat_provider = get_chat_provider(settings, ollama)
        self._document_service = DocumentService(settings, ollama, db)
        self._rag = RAGPipeline(
            settings,
            ollama,
            self._chat_provider,
            self._vector_store,
            memory_manager,
        )

    def _scoped_session_id(self, user_id: UUID, session_id: str) -> str:
        return f"{user_id}:{session_id}"

    def verify_doc_access(self, user_id: UUID, doc_id: str) -> None:
        self._document_service.get_owned_document(doc_id, user_id)

    async def stream_chat(
        self,
        user_id: UUID,
        session_id: str,
        request: ChatRequest,
    ) -> AsyncGenerator[str, None]:
        await self._ollama.require_available()
        scoped_session = self._scoped_session_id(user_id, session_id)

        async for event in self._rag.astream_response(
            scoped_session,
            request.question,
            request.doc_id,
        ):
            safe_event: dict = {}

            for key, value in event.items():
                if key == "sources" and value:
                    safe_event[key] = [
                        src.model_dump()
                        if isinstance(src, SourceDocument)
                        else src
                        for src in value
                    ]
                else:
                    safe_event[key] = value

            payload = json.dumps(safe_event)
            yield f"data: {payload}\n\n"
