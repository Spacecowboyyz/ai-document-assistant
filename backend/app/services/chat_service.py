from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator
from uuid import UUID

KEEPALIVE_INTERVAL_SECONDS = 15.0

from sqlalchemy.orm import Session

from app.config import Settings
from app.core.memory import MemoryManager
from app.core.provider_factory import get_chat_provider, get_embedding_provider
from app.core.providers import AIAvailability
from app.core.rag_pipeline import RAGPipeline
from app.core.vector_store import ChromaVectorStore
from app.schemas.chat import ChatRequest, SourceDocument
from app.services.document_service import DocumentService


class ChatService:
    def __init__(
        self,
        settings: Settings,
        ai: AIAvailability,
        memory_manager: MemoryManager,
        db: Session,
    ) -> None:
        self._settings = settings
        self._ai = ai
        self._memory_manager = memory_manager
        self._db = db
        embedding = get_embedding_provider(settings, ai)
        self._vector_store = ChromaVectorStore(settings, embedding)
        self._chat_provider = get_chat_provider(settings, ai)
        self._document_service = DocumentService(settings, ai, db)
        self._rag = RAGPipeline(
            settings,
            ai,
            self._chat_provider,
            self._vector_store,
            memory_manager,
        )

    def _scoped_session_id(self, user_id: UUID, session_id: str) -> str:
        return f"{user_id}:{session_id}"

    def verify_doc_access(self, user_id: UUID, doc_id: str) -> None:
        self._document_service.get_owned_document(doc_id, user_id)

    @staticmethod
    def _keepalive_sse_line() -> str:
        payload = json.dumps({"token": "", "done": False, "keepalive": True})
        return f"data: {payload}\n\n"

    def _event_to_sse_line(self, event: dict[str, Any]) -> str:
        safe_event: dict[str, Any] = {}
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
        return f"data: {json.dumps(safe_event)}\n\n"

    async def stream_chat(
        self,
        user_id: UUID,
        session_id: str,
        request: ChatRequest,
    ) -> AsyncGenerator[str, None]:
        await self._ai.require_available()
        scoped_session = self._scoped_session_id(user_id, session_id)

        rag_stream = self._rag.astream_response(
            scoped_session,
            request.question,
            request.doc_id,
        )
        rag_iter = rag_stream.__aiter__()

        while True:
            try:
                event = await asyncio.wait_for(
                    rag_iter.__anext__(),
                    timeout=KEEPALIVE_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                yield self._keepalive_sse_line()
                continue
            except StopAsyncIteration:
                break

            yield self._event_to_sse_line(event)
