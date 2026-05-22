# PROJECT_CONTEXT.md

Single source of truth for the **AI Document Assistant** repository. A fresh agent should read this file first before continuing development.

**Repository root:** `c:\Users\KRISH\ai-document-assistant`  
**Backend root:** `backend/`  
**Last verified state:** Phases 1–3 implemented; **28 pytest tests** passed after Phase 3; HTTPBearer Swagger change applied; optional fix needed for `deps.py` ↔ `main.py` circular import (see §10).

---

## 1. PROJECT OVERVIEW

### What this project is

A **local-first AI Document Assistant API**: users register/login with JWT, upload PDFs, documents are chunked and embedded into **ChromaDB**, and users chat over those documents via **SSE streaming** answers from a local **Ollama** LLM. No cloud LLM APIs, no paid services. Designed for Docker deployment with persistent SQLite user/document metadata.

There is **no frontend** in the repo yet—only a FastAPI backend and docs.

### Current status (what works end to end)

| Capability | Status |
|------------|--------|
| Health check | Works; always HTTP 200, independent of Ollama/DB |
| Ollama model status | Works; `GET /api/v1/models/status` public |
| User register / login / refresh / me | Works; JWT access (15m) + refresh (7d, DB-stored, rotated) |
| PDF upload (authenticated) | Works when Ollama online + models pulled; creates `DocumentMeta` + Chroma collection per `doc_id` |
| List / delete documents (authenticated) | Works; scoped to `user_id`; cross-user → 403 |
| Chat SSE (authenticated) | Works when Ollama ready; memory scoped `user_id:session_id`; doc ownership checked before stream |
| App startup with Ollama offline | Works; logs warning, does not crash |
| Upload/chat with Ollama offline | HTTP 503 with standard detail message |
| Docker build + run | Works; Alembic `upgrade head` on startup; SQLite under `data/` |
| pytest (offline) | **28 passed, 0 failed** (mocked Ollama; per-test SQLite via `tmp_path`) |
| Swagger Authorize | HTTPBearer simple token field (not OAuth2 password form) |

**Manual E2E (requires host Ollama):** `ollama serve`, `ollama pull llama3`, `ollama pull nomic-embed-text`, then upload + chat via Swagger or curl with Bearer token.

### Tech stack (every technology used)

| Layer | Technology | Version (pinned in `requirements.txt`) |
|-------|------------|----------------------------------------|
| Language | Python | 3.11 in Docker; 3.14 used locally for dev |
| Web framework | FastAPI | 0.115.6 |
| ASGI server | Uvicorn | 0.32.1 |
| Settings | pydantic-settings, python-dotenv | 2.6.1, 1.0.1 |
| Validation | Pydantic, email-validator | (via FastAPI), 2.2.0 |
| HTTP client (tests + Ollama ping) | httpx | 0.28.1 |
| Auth JWT | python-jose[cryptography] | 3.3.0 |
| Password hashing | passlib[bcrypt], bcrypt | 1.7.4, 4.0.1 |
| ORM | SQLAlchemy | 2.0.36 |
| Migrations | Alembic | 1.14.0 |
| DB | SQLite | file at `./data/app.db` (from `DATABASE_URL`) |
| Vector store | ChromaDB + langchain-chroma | chromadb 0.5.23, langchain-chroma 0.2.0 |
| LLM orchestration | LangChain (LCEL-style chain in custom pipeline) | langchain 0.3.14, langchain-core 0.3.29, langchain-community 0.3.14 |
| Text splitting | langchain-text-splitters | 0.3.5 |
| PDF extraction | PyMuPDF (`fitz`) | pymupdf 1.25.2 |
| Local embeddings | OllamaEmbeddings (langchain_community) | model `nomic-embed-text` |
| Local chat | ChatOllama (langchain_community) | model from `OLLAMA_CHAT_MODEL` (default `llama3`) |
| Ollama Python client | ollama | 0.4.7 |
| File upload | python-multipart | 0.0.20 |
| SSE | sse-starlette (available; chat uses StreamingResponse) | 2.2.1 |
| Async file I/O | aiofiles | 24.1.0 |
| Testing | pytest, pytest-asyncio, pytest-mock | 8.3.4, 0.24.0, 3.14.0 |
| Test PDF fixture | fpdf2 | 2.8.2 |
| Container | Docker python:3.11-slim | see `backend/Dockerfile` |

**Explicitly NOT used:** OpenAI API, `langchain-openai`, PostgreSQL, Redis, frontend framework.

---

## 2. COMPLETE FILE TREE

Tree covers `backend/` application and test code. Runtime/generated paths listed separately.

```
backend/
├── .env.example                          # Documented env vars template
├── .env                                  # Local secrets (gitignored) — may exist
├── alembic.ini                           # Alembic config; script_location=alembic
├── Dockerfile                            # Python 3.11 image; copies app + alembic
├── pytest.ini                            # asyncio_mode=auto; testpaths=tests
├── requirements.txt                      # All pinned Python dependencies
│
├── alembic/
│   ├── env.py                            # Alembic env; imports Base + models
│   ├── script.py.mako                    # Migration file template
│   └── versions/
│       └── 0001_initial.py               # Creates users, refresh_tokens, document_meta
│
├── app/
│   ├── __init__.py                       # Empty package marker
│   ├── main.py                           # FastAPI app, lifespan, HTTPBearer OpenAPI
│   ├── config.py                         # pydantic-settings; all env fields
│   │
│   ├── api/
│   │   ├── __init__.py                   # Mounts health + /api/v1 routers
│   │   ├── deps.py                       # ONLY DI file: get_current_user, services
│   │   └── routes/
│   │       ├── __init__.py               # Routes package marker
│   │       ├── auth.py                   # register, login, refresh, me
│   │       ├── chat.py                   # SSE chat stream endpoint
│   │       ├── documents.py              # upload, list, delete documents
│   │       ├── health.py                 # GET /health
│   │       └── models.py                 # GET /models/status
│   │
│   ├── auth/
│   │   ├── __init__.py                   # Re-exports security helpers
│   │   └── security.py                   # bcrypt hash; JWT encode/decode
│   │
│   ├── core/
│   │   ├── __init__.py                   # Package marker (Phase 2 placeholder)
│   │   ├── providers.py                  # ABCs + OllamaAvailability + 503 detail
│   │   ├── provider_factory.py           # Returns LocalEmbedding + OllamaChat
│   │   ├── embeddings.py                 # LocalEmbeddingService → OllamaEmbeddings
│   │   ├── ollama_chat.py                # OllamaChatProvider → ChatOllama stream
│   │   ├── pdf_parser.py                 # PyMuPDF + RecursiveCharacterTextSplitter
│   │   ├── vector_store.py               # Chroma PersistentClient per doc_id
│   │   ├── memory.py                     # ConversationBufferWindowMemory k=10
│   │   └── rag_pipeline.py               # Retrieval + chat stream; yields tokens
│   │
│   ├── db/
│   │   ├── __init__.py                   # Exports Base, get_db, engine helpers
│   │   ├── base.py                       # SQLAlchemy DeclarativeBase
│   │   └── database.py                   # Engine, SessionLocal, get_db()
│   │
│   ├── models/
│   │   ├── __init__.py                   # Exports User, RefreshToken, DocumentMeta
│   │   ├── user.py                       # SQLAlchemy User table
│   │   ├── token.py                      # SQLAlchemy RefreshToken table
│   │   └── document_meta.py              # SQLAlchemy DocumentMeta ownership table
│   │
│   ├── schemas/
│   │   ├── __init__.py                   # Re-exports all Pydantic models
│   │   ├── auth.py                       # Register, Login, Token, User responses
│   │   ├── chat.py                       # ChatRequest, SourceDocument, StreamToken
│   │   ├── document.py                   # Upload, DocumentInfo, Delete responses
│   │   ├── health.py                     # HealthResponse
│   │   └── models.py                     # ModelsStatusResponse
│   │
│   └── services/
│       ├── __init__.py                   # Package marker
│       ├── auth_service.py               # register, login, refresh, JWT user lookup
│       ├── chat_service.py               # SSE formatting; scoped session; ownership
│       ├── document_service.py           # PDF ingest; DocumentMeta CRUD; Chroma
│       ├── health.py                     # Builds HealthResponse from settings
│       └── models_service.py             # Ollama status snapshot for API
│
├── scripts/
│   └── generate_sample_pdf.py            # Generates tests/fixtures/sample.pdf
│
├── tests/
│   ├── __init__.py                       # Tests package marker
│   ├── conftest.py                       # Ollama mocks, db_session, app.state
│   ├── in_memory_vector_store.py         # Test double when Chroma not installable
│   ├── fixtures/
│   │   └── sample.pdf                    # 2+ page PDF; 500+ words
│   ├── test_auth.py                      # 16 auth + ownership tests
│   ├── test_documents_api.py             # 2 document API integration tests
│   ├── test_health.py                    # 2 health endpoint tests
│   ├── test_models_status.py             # 3 models status + health offline
│   ├── test_pdf_parser.py                # 3 PDF parser unit tests
│   └── test_rag.py                       # 2 RAG/memory unit tests
│
├── data/                                 # Created at runtime; gitignored
│   └── app.db                            # SQLite database (Docker volume target)
├── chroma_db/                            # Chroma persistence; gitignored
├── uploads/                              # Stored PDFs `{doc_id}.pdf`; gitignored
│   └── (legacy documents_index.json may exist from Phase 2 — superseded by DB)
```

**Repo root (non-backend) files relevant to context:**

| Path | Purpose |
|------|---------|
| `README.md` | Quick start, Docker commands, route list |
| `docs/setup.md` | Ollama setup, auth env, Docker volume commands |
| `implementation_plan.md` | Phase 1–3 plans and approval history |
| `PROJECT_CONTEXT.md` | This file |
| `.gitignore` | Ignores `.env`, `data/`, `chroma_db/`, `uploads/`, caches |
| `hello.txt` | Unrelated sample file from early scaffold |

---

## 3. PHASE COMPLETION STATUS

### Phase 1 — Backend Foundation

**Built:**

- FastAPI app with CORS, pydantic-settings, `GET /health`
- Thin routes + `services/health.py`
- 17 files: requirements, Dockerfile, app scaffold, `test_health.py`

**Verified:**

- `pytest tests/test_health.py` → 2 passed
- `docker build` + `docker run` → `/health` 200, `/docs` loads
- JSON: `{"status":"ok","version":"1.0.0","environment":"..."}`

### Phase 2 — RAG Pipeline + PDF Ingestion

**Built:**

- Local **Ollama** for embeddings (`nomic-embed-text`) and chat (`llama3` default)
- Provider abstraction: `BaseEmbeddingProvider`, `BaseChatProvider`, `OllamaAvailability`
- PDF parse (PyMuPDF), chunk (1000/200 overlap), Chroma per `doc_id`
- `RAGPipeline` with history in prompt + streaming tokens
- Routes: `/api/v1/upload`, `/documents`, `/chat/{session_id}`, `/models/status`
- Graceful degradation: startup never crashes if Ollama down; 503 on upload/chat
- 12 pytest tests (offline mocks)

**Verified:**

- 12 passed pytest (pdf_parser, rag, models_status, documents_api, health)
- Docker E2E with `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- `grep -ri openai backend/` → zero matches

**Note:** Phase 2 used JSON file `uploads/documents_index.json` for metadata; **Phase 3 replaced** with `document_meta` table (legacy file may remain on disk).

### Phase 3 — JWT Authentication + Multi-User

**Built:**

- SQLite + SQLAlchemy models: `users`, `refresh_tokens`, `document_meta`
- Alembic `0001_initial`; `alembic upgrade head` in lifespan
- JWT access (HS256, 15m) + refresh tokens (7d, stored, rotated on refresh)
- Auth routes under `/api/v1/auth/*`
- `get_current_user` in **`app/api/deps.py` only** (HTTPBearer)
- Document ownership enforcement; chat memory key `{user_id}:{session_id}`
- `test_auth.py` (16 tests) + updated `test_documents_api.py`
- Swagger **HTTPBearer** scheme in `main.py` custom OpenAPI

**Verified:**

- 28 passed pytest full suite
- Docker: migration runs, register/login works, `/health` and `/models/status` public
- Cross-user delete/chat → 403

---

## 4. ARCHITECTURE DECISIONS

### Why SQLite not PostgreSQL

- Requirement: **entire stack free**, no external DB service
- Single-file DB suits single-node Docker deployment
- Alembic migrations still supported
- Tests use **isolated** `sqlite:///{tmp_path}/test.db` per test via `db_session` fixture
- PostgreSQL explicitly deferred to a future phase

### Why Ollama not OpenAI

- Requirement: **no cloud APIs, no paid dependencies, runs offline**
- `nomic-embed-text` for embeddings, configurable chat model (default `llama3`)
- `grep -ri openai backend/` must stay **zero**
- pytest **never** calls live Ollama; all provider boundaries mocked

### Why LCEL-style pipeline not ConversationalRetrievalChain

- `ConversationalRetrievalChain` is **deprecated** in LangChain 0.3.x
- Current `rag_pipeline.py` uses:
  - Custom `_VectorRetriever` → `ChromaVectorStore.similarity_search`
  - Chat history injected into message list for `ChatOllama.astream`
  - Yields `{"token": "...", "done": false}` then final `done: true` + `sources`
- Does **not** use `create_retrieval_chain` in production code today (simpler custom flow)

### How DI works (`deps.py` is the only DI file)

All FastAPI dependencies live in **`backend/app/api/deps.py`**:

| Function | Returns | Used by |
|----------|---------|---------|
| `get_app_settings()` | `Settings` | models route |
| `get_ollama(request)` | `OllamaAvailability` from `app.state` | models, services |
| `get_memory_manager(request)` | `MemoryManager` from `app.state` | chat service |
| `get_current_user()` | `User` via HTTPBearer JWT | protected routes |
| `get_document_service()` | `DocumentService` | documents routes |
| `get_chat_service()` | `ChatService` | chat route |

**No** `auth/dependencies.py`. **No** parallel middleware DI.

`http_bearer` instance is defined in **`app/main.py`** and imported into `deps.py` (see §10 circular import note).

### How ownership works (`DocumentMeta` table)

- On upload: row `{ doc_id, user_id, filename, chunk_count, created_at }`
- `doc_id` is UUID string; also Chroma collection name `doc_{sanitized_id}` and file `uploads/{doc_id}.pdf`
- List: `SELECT` where `user_id = current_user.id`
- Delete: `get_owned_document()` → 403 `"Not authorized"` if wrong user; 403 `"Document not found or access denied"` if missing
- Chat: `verify_doc_access()` in route **before** `StreamingResponse` (so 403 is not buried in stream)

### How session isolation works (`user_id:session_id`)

In `ChatService._scoped_session_id()`:

```text
internal_key = f"{user_id}:{session_id}"
```

Passed to `RAGPipeline.astream_response(internal_key, ...)`, which uses `MemoryManager` keyed by that string. User A cannot read User B's conversation memory even with the same `session_id` path param.

`MemoryManager`: `ConversationBufferWindowMemory(k=10)`, sessions expire after **2 hours** inactivity.

### How graceful degradation works (`OllamaAvailability`)

**Startup (`main.py` lifespan):**

1. `await ollama.ping_startup()` → GET `{OLLAMA_BASE_URL}/api/tags`
2. On failure: log warning, set `online=False` — **never raises**, app starts

**Request time (`require_available()`):**

- Called before upload ingest, chat stream, embedding calls
- Re-pings `/api/tags`; checks configured chat + embed model names exist in tags
- Failure → `HTTPException(503, detail=build_ollama_unavailable_detail(settings))`

**Not gated:** `/health`, `/api/v1/models/status`, `/api/v1/auth/*` (except `/me` needs Bearer), list/delete without embeddings

**`/api/v1/models/status`:** always 200; reports `ollama: online|offline`, `models_ready: bool`

---

## 5. ALL API ENDPOINTS

Base URL: `http://localhost:8000`. Swagger: `/docs`. OpenAPI: `/openapi.json`.

### `GET /health`

| Field | Value |
|-------|-------|
| Auth | **No** |
| Request body | None |
| Response | `HealthResponse`: `{ "status": "ok", "version": string, "environment": string }` |
| Service | `services.health.get_health_status()` via `routes/health.py` |

---

### `GET /api/v1/models/status`

| Field | Value |
|-------|-------|
| Auth | **No** |
| Request body | None |
| Response | `ModelsStatusResponse`: `{ "ollama": "online"\|"offline", "chat_model": string, "embed_model": string, "models_ready": bool }` |
| Service | `services.models_service.get_models_status(ollama, settings)` |

---

### `POST /api/v1/auth/register`

| Field | Value |
|-------|-------|
| Auth | **No** |
| Request body | `RegisterRequest`: `{ "email": EmailStr, "password": string (min 8) }` |
| Response | `UserResponse`: `{ "user_id": UUID, "email": string, "created_at": datetime }` |
| Service | `auth_service.register_user(db, body)` |
| Errors | 400 email already registered; 422 invalid email/password length |

---

### `POST /api/v1/auth/login`

| Field | Value |
|-------|-------|
| Auth | **No** |
| Request body | `LoginRequest`: `{ "email", "password" }` |
| Response | `TokenResponse`: `{ "access_token", "refresh_token", "token_type": "bearer" }` |
| Service | `auth_service.login_user(db, body)` |
| Errors | 401 `"Email not found"` or `"Password incorrect"` |

---

### `POST /api/v1/auth/refresh`

| Field | Value |
|-------|-------|
| Auth | **No** (refresh token in body only, no Bearer) |
| Request body | `RefreshRequest`: `{ "refresh_token": string }` |
| Response | `TokenResponse` (new access + new refresh) |
| Service | `auth_service.refresh_tokens(db, body)` — **revokes** old refresh row |
| Errors | 401 `"Invalid token"`, `"Token revoked"`, `"Token expired"` |

---

### `GET /api/v1/auth/me`

| Field | Value |
|-------|-------|
| Auth | **Yes** — `Authorization: Bearer <access_token>` |
| Request body | None |
| Response | `UserResponse` |
| Service | Route builds from `get_current_user` → DB user (JWT validated in `auth_service.get_user_from_access_token`) |
| Errors | 401 `Not authenticated`, `Invalid token`, `Token expired` |

---

### `POST /api/v1/upload`

| Field | Value |
|-------|-------|
| Auth | **Yes** — Bearer |
| Request body | `multipart/form-data`: field `file` = PDF only, max `MAX_UPLOAD_SIZE_MB` |
| Response | `UploadResponse`: `{ "doc_id", "filename", "chunk_count", "message" }` |
| Service | `document_service.ingest_upload(file, current_user.id)` |
| Errors | 400 non-PDF; 413 too large; 503 Ollama unavailable; 500 ingest failures |

---

### `GET /api/v1/documents`

| Field | Value |
|-------|-------|
| Auth | **Yes** — Bearer |
| Request body | None |
| Response | `list[DocumentInfo]`: `[{ doc_id, filename, chunk_count, created_at }, ...]` |
| Service | `document_service.list_documents(current_user.id)` |

---

### `DELETE /api/v1/documents/{doc_id}`

| Field | Value |
|-------|-------|
| Auth | **Yes** — Bearer |
| Request body | None |
| Response | `DeleteResponse`: `{ "doc_id", "deleted": true, "message" }` |
| Service | `document_service.delete_document(doc_id, current_user.id)` |
| Errors | 403 not owner; 404 not found (when no meta and no file) |

---

### `POST /api/v1/chat/{session_id}`

| Field | Value |
|-------|-------|
| Auth | **Yes** — Bearer |
| Request body | `ChatRequest`: `{ "question": string, "doc_id": string }` |
| Response | **SSE** `text/event-stream`: lines `data: {json}\n\n` |
| SSE token event | `{ "token": string, "done": false }` |
| SSE final event | `{ "token": "", "done": true, "sources": [{ page_number, source_filename, content }, ...] }` |
| Service | `chat_service.stream_chat(user_id, session_id, body)` → `rag_pipeline.astream_response` |
| Errors | 403 doc not owned; 503 Ollama unavailable |

---

## 6. DATABASE SCHEMA

**Engine:** SQLite from `DATABASE_URL` (default `sqlite:///./data/app.db`).  
**ORM base:** `app.db.base.Base`  
**Migration:** `alembic/versions/0001_initial.py` (revision `0001_initial`)

### Table: `users`

| Column | SQLAlchemy type | Constraints / notes |
|--------|-----------------|---------------------|
| `id` | UUID | PK, default `uuid4` |
| `email` | String(255) | unique, indexed, not null; stored lowercase stripped |
| `hashed_password` | String(255) | bcrypt via passlib |
| `is_active` | Boolean | default True |
| `created_at` | DateTime(timezone=True) | UTC default |

### Table: `refresh_tokens`

| Column | Type | Constraints / notes |
|--------|------|---------------------|
| `id` | UUID | PK |
| `token` | String(512) | unique, indexed; opaque `secrets.token_urlsafe(48)` |
| `user_id` | UUID | FK → `users.id` **ON DELETE CASCADE** |
| `expires_at` | DateTime(timezone=True) | now + `REFRESH_TOKEN_EXPIRE_DAYS` |
| `created_at` | DateTime(timezone=True) | |
| `is_revoked` | Boolean | default False; True after refresh rotation |

### Table: `document_meta`

| Column | Type | Constraints / notes |
|--------|------|---------------------|
| `id` | UUID | PK |
| `doc_id` | String(64) | unique, indexed; matches Chroma/PDF filename |
| `user_id` | UUID | FK → `users.id` **ON DELETE CASCADE**, indexed |
| `filename` | String(512) | original upload name |
| `chunk_count` | Integer | chunks indexed |
| `created_at` | DateTime(timezone=True) | |

### Relationships

- `User.refresh_tokens` → one-to-many `RefreshToken`
- `User.documents` → one-to-many `DocumentMeta`
- Deleting user cascades tokens + document_meta rows (PDF/Chroma cleanup is via delete endpoint logic)

### Chroma (not SQL)

- Path: `CHROMA_DB_PATH` (default `./chroma_db`)
- Collection per document: `doc_{sanitized_doc_id}`
- Not managed by Alembic

---

## 7. ENVIRONMENT VARIABLES

All documented in `backend/.env.example`. Loaded by `app/config.py` (`Settings`).

| Variable | What it does | Default in `.env.example` |
|----------|--------------|---------------------------|
| `ENVIRONMENT` | Shown in `/health` as `environment` | `development` |
| `APP_VERSION` | Shown in `/health` as `version` | `1.0.0` |
| `CORS_ORIGINS` | Comma-separated origins; `*` = allow all | `*` |
| `HOST` | Uvicorn bind host (informational; CMD uses 0.0.0.0) | `0.0.0.0` |
| `PORT` | Uvicorn port (informational; CMD uses 8000) | `8000` |
| `OLLAMA_BASE_URL` | Ollama HTTP API root | `http://localhost:11434` |
| `OLLAMA_CHAT_MODEL` | Chat model name for tags check + ChatOllama | `llama3` |
| `OLLAMA_EMBED_MODEL` | Embedding model name | `nomic-embed-text` |
| `CHROMA_DB_PATH` | Chroma persistence directory | `./chroma_db` |
| `UPLOADS_DIR` | PDF storage `{doc_id}.pdf` | `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | Upload size limit | `50` |
| `SECRET_KEY` | JWT signing secret (HS256) | placeholder — **must change in prod** |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access JWT lifetime | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `DATABASE_URL` | SQLAlchemy URL | `sqlite:///./data/app.db` |

**Generate SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Docker Ollama on host:**

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## 8. TEST SUITE STATUS

**Config:** `backend/pytest.ini` — `asyncio_mode = auto`, `testpaths = tests`  
**Last full run:** **28 passed, 0 failed** (after Phase 3; before fixing circular import if collecting `test_documents_api` alone fails — see §10)

### `tests/test_health.py` — 2 tests

| Test | What it tests |
|------|----------------|
| `test_health_returns_ok` | `/health` 200 + default env fields |
| `test_health_uses_environment_from_env` | `/health` respects `ENVIRONMENT` / `APP_VERSION` env |

**Mocks:** `get_settings` cache cleared; no Ollama.  
**Pass/fail:** PASS

---

### `tests/test_pdf_parser.py` — 3 tests

| Test | What it tests |
|------|----------------|
| `test_parse_pdf_produces_chunks_with_metadata` | ≥2 chunks, metadata keys |
| `test_parse_empty_pdf_raises` | ValueError |
| `test_parse_corrupt_pdf_raises` | ValueError |

**Mocks:** None (uses `tests/fixtures/sample.pdf`).  
**Pass/fail:** PASS

---

### `tests/test_rag.py` — 2 tests

| Test | What it tests |
|------|----------------|
| `test_memory_window_and_expiry` | MemoryManager clear + TTL |
| `test_astream_response_yields_tokens_and_sources` | RAG stream shape |

**Mocks:** `MockChatProvider`, `MockEmbeddingProvider`, `InMemoryVectorStore` (no Chroma on Py3.14).  
**Pass/fail:** PASS

---

### `tests/test_models_status.py` — 3 tests

| Test | What it tests |
|------|----------------|
| `test_models_status_offline` | `/models/status` 200, offline |
| `test_models_status_online` | online + models_ready |
| `test_health_200_when_ollama_offline` | `/health` 200 when Ollama mocked offline |

**Mocks:** `OllamaAvailability` state / AsyncMock refresh.  
**Pass/fail:** PASS

---

### `tests/test_documents_api.py` — 2 tests

| Test | What it tests |
|------|----------------|
| `test_upload_list_delete_document` | Full doc lifecycle with Bearer |
| `test_upload_returns_503_when_ollama_offline` | 503 when offline fixture |

**Mocks:** `get_db` override → `db_session`; `mock_ollama`; `InMemoryVectorStore` + `MockEmbeddingProvider` patches.  
**Pass/fail:** PASS (may fail collection if circular import — §10)

---

### `tests/test_auth.py` — 16 tests

| Test | What it tests |
|------|----------------|
| `test_register_new_user` | 200 UserResponse |
| `test_register_duplicate_email` | 400 |
| `test_register_weak_password` | 422 |
| `test_login_valid_credentials` | tokens returned |
| `test_login_wrong_password` | 401 |
| `test_login_unknown_email` | 401 |
| `test_me_with_valid_token` | 200 |
| `test_me_without_token` | 401 Not authenticated |
| `test_me_with_expired_token` | 401 Token expired |
| `test_me_with_invalid_token` | 401 Invalid token |
| `test_refresh_rotates_tokens` | new tokens; old revoked in DB |
| `test_refresh_revoked_token` | 401 Token revoked |
| `test_upload_creates_document_meta` | DocumentMeta.user_id correct |
| `test_user_cannot_access_other_users_doc` | chat 403 |
| `test_user_cannot_delete_other_users_doc` | delete 403 |
| `test_list_documents_scoped_to_user` | user B list empty |

**Mocks:** `api_client` fixture overrides `get_db`; `mock_ollama_availability`; vector store patches for upload tests.  
**Pass/fail:** PASS

---

### Mock strategy summary

| Component | Mock approach |
|-----------|----------------|
| Ollama HTTP | `OllamaAvailability.refresh` / `require_available` AsyncMock; `offline_ollama` fixture |
| Embeddings | `MockEmbeddingProvider` — 768-dim vectors |
| Chat stream | `MockChatProvider` — yields `Hello`, ` `, `world` |
| Chroma | `InMemoryVectorStore` when chromadb not installed (local Py3.14) |
| Database | `db_session`: `sqlite:///{tmp_path}/test.db`, create/drop all tables per test |
| JWT expiry test | Manually crafted expired jwt.encode |

**Zero live Ollama calls in pytest.**

---

## 9. DOCKER SETUP

### Exact docker build command

Run from `backend/`:

```powershell
docker build -t ai-doc-assistant-backend .
```

### Exact docker run command (PowerShell)

```powershell
cd backend
docker run -p 8000:8000 `
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 `
  -v "${PWD}/data:/app/data" `
  --env-file .env `
  ai-doc-assistant-backend
```

**Bash equivalent:**

```bash
docker run -p 8000:8000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v "$(pwd)/data:/app/data" \
  --env-file .env \
  ai-doc-assistant-backend
```

### What the volume mount does

- Maps host `backend/data/` → container `/app/data/`
- Persists **`app.db`** (SQLite) across container restarts
- Users, refresh tokens, and `document_meta` survive redeploys
- Without mount, DB is ephemeral inside container layer

### What happens on container startup

1. Uvicorn loads `app.main:app`
2. **Lifespan** runs:
   - `mkdir` `uploads/`, `chroma_db/`, `data/`
   - **`alembic upgrade head`** (applies `0001_initial` if needed)
   - `OllamaAvailability.ping_startup()` — non-fatal if fails
   - `app.state.ollama_availability`, `app.state.memory_manager`
3. Serves on `0.0.0.0:8000`
4. On shutdown: closes Ollama httpx client

**Image contents:** `app/`, `alembic/`, `alembic.ini`, installed pip deps. Tests **not** copied into image.

---

## 10. KNOWN ISSUES + FIXES APPLIED

### Phase 1 / infra

| Issue | Fix |
|-------|-----|
| Docker daemon not running on first verify | User started Docker Desktop; documented retry |
| PowerShell `&&` invalid | Use `;` for command chaining |

### Phase 2

| Issue | Fix |
|-------|-----|
| `IndentationError` in `chat_service.py` stream loop | Reformatted `async for` body |
| SSE `sources` serialization — `SourceDocument` vs LangChain `Document` | `chat_service` uses `model_dump()` for `SourceDocument`; route calls `verify_doc_access` **before** stream so 403 not lost in generator |
| Chroma not installable on local Python 3.14 | Tests use `InMemoryVectorStore`; Docker 3.11 uses real Chroma |
| `documents_index.json` metadata | Replaced by `document_meta` in Phase 3 |
| LangChain deprecations (`OllamaEmbeddings`, `ChatOllama`, `ConversationBufferWindowMemory`) | Warnings only; still functional |
| `chat_service` expected `doc.page_content` on sources | RAG yields `SourceDocument` pydantic models |

### Phase 3

| Issue | Fix |
|-------|-----|
| Chat 403 not returned when ownership fails inside stream | `verify_doc_access()` moved to `routes/chat.py` before `StreamingResponse` |
| OAuth2 password form in Swagger | Replaced with `HTTPBearer` + `custom_openapi()` in `main.py` |

### Remaining known issues

| Issue | Severity | Recommended fix |
|-------|----------|-----------------|
| **Circular import:** `deps.py` imports `http_bearer` from `app.main`, while `main.py` imports `api_router` → routes → `deps` | Medium | Move `http_bearer = HTTPBearer(...)` to `app/security_http.py` or `app/api/security.py`; import from there in both `main.py` (OpenAPI) and `deps.py` |
| `GET /health` route lacks explicit `response_model=HealthResponse` | Low | Add for OpenAPI clarity |
| `uploads/documents_index.json` may still exist | Low | Legacy; safe to delete; unused by Phase 3 code |
| Live upload requires Ollama models pulled (`models_ready: true`) | Expected | Document in `docs/setup.md` |
| pytest emits many asyncio/LangChain deprecation warnings on Py3.14 | Low | No functional failure |
| Logout endpoint not implemented | By design | Phase 3+ future |

---

## 11. WHAT COMES NEXT

### Phase 4 options (not started)

- **Frontend** (React/Next.js): login UI, upload, chat with SSE
- **Deployment hardening:** production `SECRET_KEY`, HTTPS reverse proxy, non-`*` CORS
- **PostgreSQL / Redis** — explicitly out of scope for Phase 3; only if requirements change
- **Logout endpoint** + refresh token revocation API
- **langchain-ollama** package migration (remove deprecation warnings)

### Pending tasks from current phases

- [ ] Fix `deps.py` / `main.py` circular import for robust test collection
- [ ] Remove or ignore legacy `uploads/documents_index.json`
- [ ] Optional: add `response_model` to `/health`
- [ ] Manual E2E checklist with `llama3` + `nomic-embed-text` pulled on host
- [ ] Production `.env` with real `SECRET_KEY` (never commit)

### Dependencies likely needed for future work

| Future work | Likely adds |
|-------------|-------------|
| Frontend | Node.js, React, API client |
| Postgres | `asyncpg`, `psycopg2`, Alembic revision 0002 |
| Logout | No new packages |
| CI | GitHub Actions, `pytest` + `docker build` |

---

## 12. HOW TO RESUME IN A NEW CHAT

**Ready-to-paste agent briefing:**

> You are continuing the **AI Document Assistant** at `c:\Users\KRISH\ai-document-assistant`. Read **`PROJECT_CONTEXT.md`** (this file) and **`implementation_plan.md`** first. The **backend** (`backend/`) is a FastAPI app: **Phase 1** health scaffold, **Phase 2** local Ollama RAG (PDF → PyMuPDF chunks → Chroma `nomic-embed-text` embeddings → SSE chat via `ChatOllama`), **Phase 3** JWT auth (SQLite `users` / `refresh_tokens` / `document_meta`, Alembic `0001_initial`, Bearer via **`app/api/deps.py` only**). Public routes: `/health`, `/api/v1/models/status`, auth register/login/refresh. Protected: `/auth/me`, upload, documents, chat. Ollama offline must not crash startup (`OllamaAvailability`); upload/chat return 503. Tests: **28 offline pytest** with mocked Ollama and per-test SQLite in `tmp_path`. Docker: build from `backend/`, run with `-v "${PWD}/data:/app/data"` and `OLLAMA_BASE_URL=http://host.docker.internal:11434`. No OpenAI, no PostgreSQL. Swagger uses **HTTPBearer** (defined in `main.py`, imported in `deps.py`—fix circular import by moving bearer to a small module if tests fail on collect). Run `cd backend && pytest -q` before changes. Do not break `/health` or public model status without auth.

---

*End of PROJECT_CONTEXT.md*
