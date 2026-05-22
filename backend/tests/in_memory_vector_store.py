from __future__ import annotations

from typing import Dict, List

from langchain_core.documents import Document

from app.config import Settings
from app.core.providers import BaseEmbeddingProvider


class InMemoryVectorStore:
    _data: Dict[str, List[Document]] = {}

    def __init__(
        self,
        settings: Settings,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self._settings = settings
        self._embedding_provider = embedding_provider

    async def add_documents(self, doc_id: str, documents: List[Document]) -> None:
        await self._embedding_provider.embed_documents(
            [doc.page_content for doc in documents]
        )
        self._data[doc_id] = list(documents)

    async def similarity_search(
        self,
        doc_id: str,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
    ) -> List[Document]:
        await self._embedding_provider.embed_query(query)
        docs = self._data.get(doc_id, [])
        return docs[:k]

    def delete_collection(self, doc_id: str) -> None:
        self._data.pop(doc_id, None)

    def list_collections(self) -> list[str]:
        return list(self._data.keys())

    def get_chunk_count(self, doc_id: str) -> int:
        return len(self._data.get(doc_id, []))
