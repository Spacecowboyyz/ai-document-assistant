import pytest

from app.core.memory import MemoryManager
from app.core.rag_pipeline import RAGPipeline
from tests.conftest import MockChatProvider, MockEmbeddingProvider
from tests.in_memory_vector_store import InMemoryVectorStore


@pytest.mark.asyncio
async def test_memory_window_and_expiry(monkeypatch):
    monkeypatch.setattr("app.core.memory.SESSION_TTL_SECONDS", 1)
    manager = MemoryManager()
    manager.get_memory("session-a")
    assert "session-a" in manager.list_sessions()
    manager.clear_memory("session-a")
    assert "session-a" not in manager.list_sessions()


@pytest.mark.asyncio
async def test_astream_response_yields_tokens_and_sources(
    mock_settings,
    mock_ollama_availability,
    tmp_path,
):
    mock_settings.uploads_path.mkdir(parents=True, exist_ok=True)
    mock_settings.chroma_path.mkdir(parents=True, exist_ok=True)

    embedding = MockEmbeddingProvider()
    InMemoryVectorStore._data.clear()
    vector_store = InMemoryVectorStore(mock_settings, embedding)
    from langchain_core.documents import Document

    await vector_store.add_documents(
        "doc-1",
        [
            Document(
                page_content="Retrieval augmented generation helps answer questions.",
                metadata={
                    "page_number": 1,
                    "source_filename": "sample.pdf",
                    "chunk_index": 0,
                },
            )
        ],
    )

    pipeline = RAGPipeline(
        mock_settings,
        mock_ollama_availability,
        MockChatProvider(),
        vector_store,
        MemoryManager(),
    )

    events = []
    async for event in pipeline.astream_response("sess-1", "What is RAG?", "doc-1"):
        events.append(event)

    assert any(e.get("token") == "Hello" for e in events)
    final = events[-1]
    assert final["done"] is True
    assert final["sources"]
    assert final["sources"][0].source_filename == "sample.pdf"
