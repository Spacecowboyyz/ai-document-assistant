from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.main import app
from tests.conftest import MockEmbeddingProvider
from tests.in_memory_vector_store import InMemoryVectorStore


@pytest.fixture
async def api_client(db_session, mock_ollama_availability, mock_settings):
    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.state.ai_availability = mock_ollama_availability
    app.state.ollama_availability = mock_ollama_availability
    from app.core.memory import MemoryManager

    app.state.memory_manager = MemoryManager()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


async def _auth_headers(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_upload_list_delete_document(api_client, sample_pdf_path):
    headers = await _auth_headers(api_client, "docuser@example.com")
    InMemoryVectorStore._data.clear()

    with (
        patch(
            "app.services.document_service.get_embedding_provider",
            return_value=MockEmbeddingProvider(),
        ),
        patch(
            "app.services.document_service.ChromaVectorStore",
            InMemoryVectorStore,
        ),
    ):
        with sample_pdf_path.open("rb") as pdf_file:
            upload_response = await api_client.post(
                "/api/v1/upload",
                headers=headers,
                files={"file": ("sample.pdf", pdf_file, "application/pdf")},
            )

        assert upload_response.status_code == 200
        payload = upload_response.json()
        assert payload["chunk_count"] > 0
        doc_id = payload["doc_id"]

        list_response = await api_client.get("/api/v1/documents", headers=headers)
        assert list_response.status_code == 200
        documents = list_response.json()
        assert any(item["doc_id"] == doc_id for item in documents)

        delete_response = await api_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers=headers,
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True


@pytest.mark.asyncio
async def test_upload_returns_503_when_ollama_offline(
    api_client,
    sample_pdf_path,
    offline_ollama,
):
    app.state.ai_availability = offline_ollama
    app.state.ollama_availability = offline_ollama
    headers = await _auth_headers(api_client, "offline@example.com")

    with sample_pdf_path.open("rb") as pdf_file:
        response = await api_client.post(
            "/api/v1/upload",
            headers=headers,
            files={"file": ("sample.pdf", pdf_file, "application/pdf")},
        )

    assert response.status_code == 503
    assert "Local AI models unavailable" in response.json()["detail"]
