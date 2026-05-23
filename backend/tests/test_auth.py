from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import select

from app.config import get_settings
from app.models.document_meta import DocumentMeta
from app.models.token import RefreshToken


@pytest.fixture
async def api_client(db_session, mock_ollama_availability, mock_settings):
    from app.api.deps import get_db
    from app.main import app

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


@pytest.mark.asyncio
async def test_register_new_user(api_client):
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "user_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(api_client):
    payload = {"email": "dup@example.com", "password": "password123"}
    first = await api_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 200
    second = await api_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(api_client):
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_valid_credentials(api_client):
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(api_client):
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": "password123"},
    )
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "wrongpass1"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Password incorrect"


@pytest.mark.asyncio
async def test_login_unknown_email(api_client):
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "password123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email not found"


@pytest.mark.asyncio
async def test_me_with_valid_token(api_client):
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "password123"},
    )
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_me_without_token(api_client):
    response = await api_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_me_with_expired_token(api_client, mock_settings):
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": str(uuid4()),
            "email": "exp@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


@pytest.mark.asyncio
async def test_me_with_invalid_token(api_client):
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(api_client, db_session):
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    old_refresh = login.json()["refresh_token"]

    refreshed = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refreshed.status_code == 200
    new_data = refreshed.json()
    assert new_data["access_token"]
    assert new_data["refresh_token"] != old_refresh

    row = db_session.scalar(
        select(RefreshToken).where(RefreshToken.token == old_refresh)
    )
    assert row is not None
    assert row.is_revoked is True


@pytest.mark.asyncio
async def test_refresh_revoked_token(api_client):
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "revoked@example.com", "password": "password123"},
    )
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "revoked@example.com", "password": "password123"},
    )
    old_refresh = login.json()["refresh_token"]
    await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    again = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert again.status_code == 401
    assert again.json()["detail"] == "Token revoked"


@pytest.mark.asyncio
async def test_upload_creates_document_meta(api_client, db_session, sample_pdf_path):
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "uploader@example.com", "password": "password123"},
    )
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "uploader@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with sample_pdf_path.open("rb") as pdf_file:
        from tests.in_memory_vector_store import InMemoryVectorStore
        from unittest.mock import patch
        from tests.conftest import MockEmbeddingProvider

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
            response = await api_client.post(
                "/api/v1/upload",
                headers=headers,
                files={"file": ("sample.pdf", pdf_file, "application/pdf")},
            )

    assert response.status_code == 200
    doc_id = response.json()["doc_id"]
    meta = db_session.scalar(
        select(DocumentMeta).where(DocumentMeta.doc_id == doc_id)
    )
    assert meta is not None
    assert meta.filename == "sample.pdf"
    assert meta.chunk_count > 0


async def _register_and_login(client, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_doc(api_client, db_session, sample_pdf_path):
    token_a = await _register_and_login(api_client, "usera@example.com")
    token_b = await _register_and_login(api_client, "userb@example.com")

    with sample_pdf_path.open("rb") as pdf_file:
        from unittest.mock import patch
        from tests.conftest import MockEmbeddingProvider
        from tests.in_memory_vector_store import InMemoryVectorStore

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
            upload = await api_client.post(
                "/api/v1/upload",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": ("sample.pdf", pdf_file, "application/pdf")},
            )
    doc_id = upload.json()["doc_id"]

    chat = await api_client.post(
        f"/api/v1/chat/session-1",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"question": "What is this?", "doc_id": doc_id},
    )
    assert chat.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_delete_other_users_doc(api_client, sample_pdf_path):
    token_a = await _register_and_login(api_client, "dela@example.com")
    token_b = await _register_and_login(api_client, "delb@example.com")

    with sample_pdf_path.open("rb") as pdf_file:
        from unittest.mock import patch
        from tests.conftest import MockEmbeddingProvider
        from tests.in_memory_vector_store import InMemoryVectorStore

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
            upload = await api_client.post(
                "/api/v1/upload",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": ("sample.pdf", pdf_file, "application/pdf")},
            )
    doc_id = upload.json()["doc_id"]

    deleted = await api_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert deleted.status_code == 403
    assert deleted.json()["detail"] == "Not authorized"


@pytest.mark.asyncio
async def test_list_documents_scoped_to_user(api_client, sample_pdf_path):
    token_a = await _register_and_login(api_client, "lista@example.com")
    token_b = await _register_and_login(api_client, "listb@example.com")

    with sample_pdf_path.open("rb") as pdf_file:
        from unittest.mock import patch
        from tests.conftest import MockEmbeddingProvider
        from tests.in_memory_vector_store import InMemoryVectorStore

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
            await api_client.post(
                "/api/v1/upload",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": ("sample.pdf", pdf_file, "application/pdf")},
            )

    list_b = await api_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_b.status_code == 200
    assert list_b.json() == []
