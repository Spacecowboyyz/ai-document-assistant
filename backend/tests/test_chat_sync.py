from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.memory import MemoryManager
from app.schemas.chat import ChatRequest, SourceDocument
from app.services.chat_service import ChatService


async def _mock_rag_stream(*_args, **_kwargs):
    yield {"token": "Hello", "done": False}
    yield {"token": " world", "done": False}
    yield {
        "token": "",
        "done": True,
        "sources": [
            SourceDocument(
                page_number=1,
                source_filename="sample.pdf",
                content="context",
            )
        ],
    }


@pytest.mark.asyncio
async def test_chat_sync_collects_full_response(
    mock_settings,
    mock_ollama_availability,
    db_session,
):
    from app.models.document_meta import DocumentMeta
    from datetime import datetime, timezone

    user_id = uuid4()
    doc_id = str(uuid4())
    db_session.add(
        DocumentMeta(
            doc_id=doc_id,
            user_id=user_id,
            filename="sample.pdf",
            chunk_count=1,
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    ai = mock_ollama_availability
    memory = MemoryManager()
    service = ChatService(mock_settings, ai, memory, db_session)
    service._rag.astream_response = _mock_rag_stream

    result = await service.chat_sync(
        user_id,
        "session-1",
        ChatRequest(question="What is this?", doc_id=doc_id),
    )

    assert result.answer == "Hello world"
    assert len(result.sources) == 1
    assert result.sources[0].source_filename == "sample.pdf"


@pytest.mark.asyncio
async def test_chat_sync_endpoint(
    db_session,
    mock_ollama_availability,
    mock_settings,
    monkeypatch,
):
    from app.api.deps import get_db
    from app.main import app

    async def _patched_astream_response(self, *_args, **_kwargs):
        async for event in _mock_rag_stream():
            yield event

    monkeypatch.setattr(
        "app.core.rag_pipeline.RAGPipeline.astream_response",
        _patched_astream_response,
    )

    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.state.ai_availability = mock_ollama_availability
    app.state.ollama_availability = mock_ollama_availability
    app.state.memory_manager = MemoryManager()

    from app.models.document_meta import DocumentMeta
    from datetime import datetime, timezone

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "sync@example.com", "password": "password123"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "sync@example.com", "password": "password123"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = await client.get("/api/v1/auth/me", headers=headers)
        user_id = UUID(me.json()["user_id"])

        doc_id = str(uuid4())
        db_session.add(
            DocumentMeta(
                doc_id=doc_id,
                user_id=user_id,
                filename="sample.pdf",
                chunk_count=1,
                created_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()

        session_id = str(uuid4())
        response = await client.post(
            f"/api/v1/chat/{session_id}/sync",
            headers=headers,
            json={"question": "Summarize", "doc_id": doc_id},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Hello world"
    assert data["sources"][0]["source_filename"] == "sample.pdf"
