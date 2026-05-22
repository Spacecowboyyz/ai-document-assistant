from __future__ import annotations

import re
from typing import List

from langchain_core.documents import Document

from app.config import Settings
from app.core.providers import BaseEmbeddingProvider


def _sanitize_collection_name(doc_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_id)
    return f"doc_{safe}"


class ChromaVectorStore:
    def __init__(self, settings: Settings, embedding_provider: BaseEmbeddingProvider) -> None:
        self._settings = settings
        self._embedding_provider = embedding_provider
        self._persist_directory = str(settings.chroma_path)

    def _collection_name(self, doc_id: str) -> str:
        return _sanitize_collection_name(doc_id)

    def _get_client(self):
        import chromadb

        return chromadb.PersistentClient(path=self._persist_directory)

    async def add_documents(self, doc_id: str, documents: List[Document]) -> None:
        texts = [doc.page_content for doc in documents]
        embeddings = await self._embedding_provider.embed_documents(texts)
        metadatas = [doc.metadata for doc in documents]
        ids = [f"{doc_id}_{i}" for i in range(len(documents))]

        client = self._get_client()
        collection = client.get_or_create_collection(name=self._collection_name(doc_id))
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    async def similarity_search(
        self,
        doc_id: str,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
    ) -> List[Document]:
        query_embedding = await self._embedding_provider.embed_query(query)
        client = self._get_client()
        collection_name = self._collection_name(doc_id)
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            return []

        count = collection.count()
        if count == 0:
            return []

        n_results = min(fetch_k, count)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas"],
        )

        docs: list[Document] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for text, metadata in zip(documents, metadatas):
            if text:
                docs.append(Document(page_content=text, metadata=metadata or {}))

        return docs[:k]

    def delete_collection(self, doc_id: str) -> None:
        client = self._get_client()
        name = self._collection_name(doc_id)
        try:
            client.delete_collection(name=name)
        except Exception:
            pass

    def list_collections(self) -> list[str]:
        client = self._get_client()
        collections = client.list_collections()
        names: list[str] = []
        for col in collections:
            name = col.name if hasattr(col, "name") else str(col)
            if name.startswith("doc_"):
                names.append(name[4:])
        return names

    def get_chunk_count(self, doc_id: str) -> int:
        client = self._get_client()
        try:
            collection = client.get_collection(name=self._collection_name(doc_id))
            return collection.count()
        except Exception:
            return 0
