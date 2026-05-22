from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from app.config import Settings
from app.core.memory import MemoryManager
from app.core.providers import BaseChatProvider, OllamaAvailability
from app.core.vector_store import ChromaVectorStore
from app.schemas.chat import SourceDocument

logger = logging.getLogger(__name__)


class _VectorRetriever:
    def __init__(self, vector_store: ChromaVectorStore, doc_id: str) -> None:
        self._vector_store = vector_store
        self._doc_id = doc_id

    async def ainvoke(self, query: str) -> list[Document]:
        return await self._vector_store.similarity_search(
            self._doc_id,
            query,
            k=5,
            fetch_k=20,
        )


class RAGPipeline:
    def __init__(
        self,
        settings: Settings,
        ollama: OllamaAvailability,
        chat_provider: BaseChatProvider,
        vector_store: ChromaVectorStore,
        memory_manager: MemoryManager,
    ) -> None:
        self._settings = settings
        self._ollama = ollama
        self._chat_provider = chat_provider
        self._vector_store = vector_store
        self._memory_manager = memory_manager
        self._source_docs: list[Document] = []

    def _documents_to_sources(self, docs: list[Document]) -> list[SourceDocument]:
        sources: list[SourceDocument] = []
        for doc in docs:
            metadata = doc.metadata or {}
            sources.append(
                SourceDocument(
                    page_number=int(metadata.get("page_number", 0)),
                    source_filename=str(metadata.get("source_filename", "")),
                    content=doc.page_content[:500],
                )
            )
        return sources

    async def astream_response(
        self,
        session_id: str,
        question: str,
        doc_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        await self._ollama.require_available()

        retriever = _VectorRetriever(self._vector_store, doc_id)
        history = self._memory_manager.get_history_messages(session_id)

        docs = await retriever.ainvoke(question)
        self._source_docs = docs
        context = "\n\n".join(doc.page_content for doc in docs)

        messages = [
            (
                "system",
                f"You are a helpful assistant. Answer using only this context:\n{context}",
            ),
        ]
        for msg in history:
            if isinstance(msg, HumanMessage):
                messages.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(("assistant", msg.content))
        messages.append(("human", question))

        full_answer = ""
        async for token in self._chat_provider.astream(messages):
            full_answer += token
            yield {"token": token, "done": False}

        self._memory_manager.append_exchange(session_id, question, full_answer)
        yield {
            "token": "",
            "done": True,
            "sources": self._documents_to_sources(self._source_docs),
        }
