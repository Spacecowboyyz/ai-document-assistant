# Phase 1 — Backend Foundation: Implementation Plan

**Status:** Awaiting approval — no backend code will be written until you approve this plan.

**Scope:** FastAPI scaffold under `backend/`, health check only. No RAG, PDF, DB, or frontend.

---

## Architecture notes

| Constraint | How we satisfy it |
|------------|-------------------|
| Async-first | All route handlers use `async def`; tests use `httpx.AsyncClient` with ASGI transport. |
| Thin routes | `health.py` only wires HTTP → service; response building lives in `app/services/health.py`. |
| Modular routes | Health lives in `app/api/routes/health.py`; future domains get their own route modules. |
| No stubs in reserved dirs | `core/`, `models/`, and package `__init__.py` files are empty but valid; no TODO placeholders. |

### Deviations from the diagram (required by your rules)

The specified tree does not include a **service layer** or a **health schema** file. To honor *“thin routes, logic in service layer”* without putting logic in `core/` (reserved for Phase 2 RAG), the plan adds:

| Extra file | Reason |
|------------|--------|
| `app/__init__.py` | Makes `app` a proper Python package (required for imports). |
| `app/services/__init__.py` | Service package root. |
| `app/services/health.py` | Health status logic (version + environment from settings). |
| `app/schemas/health.py` | Pydantic `HealthResponse` model used by the service and OpenAPI. |

If you prefer **zero** files outside the diagram, say so and we can fold the service function into `config.py` (not ideal) or relax the service-layer rule for `/health` only.

---

## Every file to create

| # | File | What it does (one sentence) |
|---|------|-----------------------------|
| 1 | `backend/requirements.txt` | Pins runtime and test dependencies (`fastapi`, `uvicorn`, `pydantic-settings`, `python-dotenv`, `pytest`, `httpx`, `pytest-asyncio`). |
| 2 | `backend/.env.example` | Documents all environment variables with safe defaults for local/Docker dev. |
| 3 | `backend/app/__init__.py` | Marks `app` as an installable Python package. |
| 4 | `backend/app/config.py` | Loads settings from `.env` via `pydantic-settings` (environment, CORS, app version, host/port). |
| 5 | `backend/app/schemas/__init__.py` | Exports schema types for clean imports (starts with `HealthResponse`). |
| 6 | `backend/app/schemas/health.py` | Defines `HealthResponse` Pydantic model matching the `/health` JSON contract. |
| 7 | `backend/app/services/__init__.py` | Marks the service layer package. |
| 8 | `backend/app/services/health.py` | Builds and returns `HealthResponse` using `Settings` (no HTTP concerns). |
| 9 | `backend/app/core/__init__.py` | Empty package placeholder for Phase 2 RAG pipeline. |
| 10 | `backend/app/models/__init__.py` | Empty package placeholder for Phase 2 DB models. |
| 11 | `backend/app/api/__init__.py` | Aggregates API routers and exposes `api_router` for `main.py`. |
| 12 | `backend/app/api/routes/__init__.py` | Marks routes subpackage. |
| 13 | `backend/app/api/routes/health.py` | Defines `GET /health` async route that delegates to the health service. |
| 14 | `backend/app/main.py` | Creates FastAPI app, configures CORS from settings, registers routers, optional lifespan hook. |
| 15 | `backend/tests/__init__.py` | Makes `tests` a package for pytest discovery. |
| 16 | `backend/tests/test_health.py` | Pytest async test asserting `/health` returns 200 and expected JSON fields. |
| 17 | `backend/Dockerfile` | `python:3.11-slim` image, installs deps, runs `uvicorn` on port 8000. |

**Total: 17 files** (13 from your tree + 4 supporting files above).

---

## Exact creation order

Dependencies flow top-down: config and schemas before services, services before routes, routes before `main.py`, app before tests and Docker.

```
1.  backend/requirements.txt
2.  backend/.env.example
3.  backend/app/__init__.py
4.  backend/app/config.py
5.  backend/app/schemas/__init__.py
6.  backend/app/schemas/health.py
7.  backend/app/services/__init__.py
8.  backend/app/services/health.py
9.  backend/app/core/__init__.py
10. backend/app/models/__init__.py
11. backend/app/api/routes/__init__.py
12. backend/app/api/routes/health.py
13. backend/app/api/__init__.py          # imports health router, builds api_router
14. backend/app/main.py
15. backend/tests/__init__.py
16. backend/tests/test_health.py
17. backend/Dockerfile
```

---

## Planned behavior (per file group)

### `config.py` / `.env.example`

**Settings fields (env-backed):**

| Variable | Purpose | Default in `.env.example` |
|----------|---------|---------------------------|
| `ENVIRONMENT` | Returned in `/health` as `environment` | `development` |
| `APP_VERSION` | Returned in `/health` as `version` | `1.0.0` |
| `CORS_ORIGINS` | Comma-separated origins; `*` = allow all (dev) | `*` |
| `HOST` | Uvicorn bind host (Dockerfile CMD) | `0.0.0.0` |
| `PORT` | Uvicorn bind port | `8000` |

`CORS_ORIGINS` parsed to a list; if the value is `*`, `CORSMiddleware` uses `allow_origins=["*"]`.

### `/health` contract

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development"
}
```

- `status`: always `"ok"` when the app is running (no external deps yet).
- `version` / `environment`: from `Settings`, not hardcoded in the route.

### `main.py`

- `FastAPI(title="AI Document Assistant API", version=settings.app_version)`
- CORS middleware from settings
- Include `api_router` with prefix `""` so health is `GET /health` (not `/api/health` unless you prefer a prefix — default plan is root-level `/health`)
- No RAG/DB startup logic

### `requirements.txt` (pinned versions)

```
fastapi==0.115.6
uvicorn[standard]==0.32.1
pydantic-settings==2.6.1
python-dotenv==1.0.1
pytest==8.3.4
httpx==0.28.1
pytest-asyncio==0.24.0
```

### `Dockerfile`

- Base: `python:3.11-slim`
- `WORKDIR /app`
- Copy `requirements.txt` → `pip install`
- Copy application code
- `EXPOSE 8000`
- `CMD` runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### `tests/test_health.py`

- Uses `pytest` + `pytest-asyncio` + `httpx.AsyncClient` against `app.main:app`
- Asserts status 200, `status == "ok"`, `version`, and `environment` match test env overrides

---

## Post-implementation verification (after your approval)

All commands run from `backend/`:

| Step | Command / check |
|------|-----------------|
| 1 | `docker build -t ai-doc-assistant-backend .` |
| 2 | `docker run -p 8000:8000 --env-file .env.example ai-doc-assistant-backend` |
| 3 | `GET http://localhost:8000/health` → HTTP 200 + JSON above |
| 4 | `GET http://localhost:8000/docs` → Swagger UI loads |
| 5 | `pytest` (local, optional but will run before sign-off) |
| 6 | Fix any build/runtime/test failures before marking Phase 1 complete |

---

## Out of scope (confirmed)

- Frontend
- RAG, PDF parsing, embeddings, vector store
- Database models/migrations
- Authentication
- `docker-compose` changes (unless you ask later)

---

## Approval

Reply **approve** (or note changes, e.g. remove `app/services/`, add `/api` prefix, different pinned versions). After approval, implementation will follow the order above and run the verification steps.

---

# Phase 2 — RAG Pipeline + PDF Ingestion: Implementation Plan

**Status:** Awaiting approval — no Phase 2 code will be written until you approve this section.

**Scope:** PDF upload/ingestion, ChromaDB vector storage, **fully local Ollama** embeddings + chat with SSE streaming. **No cloud APIs, no paid dependencies, runs offline.** No frontend, auth, PostgreSQL, or Redis.

**Provider change (vs. earlier draft):** OpenAI / `langchain-openai` / `openai` package **removed**. All LLM + embedding calls go through **Ollama** behind provider abstractions.

**Prerequisite:** Phase 1 verified (17 files, `/health`, Docker, pytest).

---

## Phase 2 architecture notes

| Constraint | How we satisfy it |
|------------|-------------------|
| Phase 1 intact | `GET /health` unchanged at root; `health.py` / `health` service untouched. |
| `/api/v1` prefix | New routers mounted under `APIRouter(prefix="/api/v1")` in `api/__init__.py`. |
| `main.py` changes only | Lifespan hook creates `UPLOADS_DIR` + `CHROMA_DB_PATH`; no business logic added. |
| Async-first | Routes and services are `async def`; blocking I/O via `asyncio.to_thread`. |
| Thin routes | `documents.py` / `chat.py` only validate HTTP + delegate to services. |
| Provider abstraction | Routes/services depend on `BaseEmbeddingProvider` / `BaseChatProvider` only; Ollama concrete classes live under `app/core/`. |
| LangChain (current) | LCEL: `create_history_aware_retriever` + `create_stuff_documents_chain` + `create_retrieval_chain`; **no** deprecated `ConversationalRetrievalChain`. |
| LLM + embeddings | `ChatOllama` + `OllamaEmbeddings` from `langchain_community`; model names + base URL from settings only. |
| Chroma MMR | `ChromaVectorStore` wraps `langchain_chroma.Chroma` per `doc_id` collection with `search_type="mmr"`, `k=5`, `fetch_k=20`. |
| Model errors | Request-time: standard **503** payload if Ollama offline or models missing — **no silent fallback** to another model. |
| Graceful degradation | Startup **never crashes** if Ollama is offline; `/health` always **200** (app health only); AI endpoints return **503** when models unavailable. |
| Dual Python | Pins for **Python 3.11 (Docker)** + local 3.14; pytest uses mocks, not installed Ollama models. |
| Tests fully offline | **All pytest suites mock Ollama** — no `ollama serve`, no pulled models required (see [Test mocking strategy](#test-mocking-strategy-no-live-ollama-in-pytest)). |
| No OpenAI in tree | Post-implementation: `grep -r "openai" backend/` must return **zero** results. |

### Router layout after Phase 2

```
GET  /health                          # Phase 1 — unchanged; 200 even if Ollama offline
GET  /api/v1/models/status            # Ollama connectivity + model readiness (no 503)
POST /api/v1/upload                   # 503 if Ollama/models unavailable
GET  /api/v1/documents                # No Ollama required (filesystem/Chroma metadata only)
DELETE /api/v1/documents/{doc_id}     # No Ollama required
POST /api/v1/chat/{session_id}        # SSE; 503 if Ollama/models unavailable
```

---

## Phase 1 files to modify (7 files)

| File | Modification (additive only) |
|------|--------------------------------|
| `backend/requirements.txt` | Append pinned LangChain, Chroma, PyMuPDF, **ollama**, multipart, SSE, aiofiles, test helpers (`fpdf2`, `pytest-mock`). **Do not add** `openai` or `langchain-openai`. |
| `backend/.env.example` | Add `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL`, `CHROMA_DB_PATH`, `UPLOADS_DIR`, `MAX_UPLOAD_SIZE_MB`. |
| `backend/app/config.py` | Add Ollama + storage settings + `max_upload_size_bytes`; **no** API keys. |
| `backend/app/main.py` | Lifespan: `mkdir` uploads/chroma; **non-blocking Ollama ping** (`/api/tags`); log warning if offline — **never raise**. Store `OllamaAvailability` on `app.state`. |
| `backend/app/api/__init__.py` | Add `v1_router` with prefix `/api/v1`; include `documents`, `chat`, **`models`** routers; keep `health.router` at root. |
| `backend/app/schemas/__init__.py` | Re-export `document`, `chat`, and **`models`** schema types. |
| `backend/.gitignore` (repo root) | Ignore `uploads/`, `chroma_db/`, `backend/uploads/`, `backend/chroma_db/` (recommended; keeps dev artifacts out of git). |

**Not modified:** `health.py`, `services/health.py`, `schemas/health.py`, `Dockerfile` (startup creates dirs), `tests/test_health.py`.

**Optional export-only touch (no logic change):** `app/services/__init__.py`, `app/core/__init__.py` — add `__all__` for discoverability.

---

## Every new file to create (25 files)

| # | File | What it does (one sentence) |
|---|------|-----------------------------|
| 1 | `backend/app/schemas/document.py` | Pydantic models: `UploadResponse`, `DocumentInfo`, `DeleteResponse`. |
| 2 | `backend/app/schemas/chat.py` | Pydantic models: `ChatRequest`, `SourceDocument`, `StreamToken` (OpenAPI/docs). |
| 3 | `backend/app/schemas/models.py` | Pydantic model: `ModelsStatusResponse` for `GET /api/v1/models/status`. |
| 4 | `backend/app/core/providers.py` | ABCs + **`OllamaAvailability`** (startup ping, request-time checks, shared **503 detail** constant). |
| 5 | `backend/app/core/provider_factory.py` | Returns concrete Ollama providers from `Settings` (swap providers here later, zero route changes). |
| 6 | `backend/app/core/pdf_parser.py` | Async-wrapped PyMuPDF extraction + `RecursiveCharacterTextSplitter` → `List[Document]` with page/chunk metadata. |
| 7 | `backend/app/core/embeddings.py` | `LocalEmbeddingService(BaseEmbeddingProvider)` via `OllamaEmbeddings`, model from `OLLAMA_EMBED_MODEL`. |
| 8 | `backend/app/core/ollama_chat.py` | `OllamaChatProvider(BaseChatProvider)` wrapping `ChatOllama` with streaming + 503 via `OllamaAvailability`. |
| 9 | `backend/app/core/vector_store.py` | `ChromaVectorStore` — per-`doc_id` collections, add/search(MMR)/delete/list on `CHROMA_DB_PATH`. |
| 10 | `backend/app/core/memory.py` | `MemoryManager` — `ConversationBufferWindowMemory(k=10)` per session, 2-hour inactivity expiry. |
| 11 | `backend/app/core/rag_pipeline.py` | `RAGPipeline` uses `BaseChatProvider` + retrieval chain; `astream_response()` yields tokens + final sources. |
| 12 | `backend/app/services/document_service.py` | Ingest/list/delete — **`require_ollama_available()`** before embed; stream PDF → parser → embed → Chroma. |
| 13 | `backend/app/services/chat_service.py` | `stream_chat` — **`require_ollama_available()`** then SSE via `RAGPipeline`. |
| 14 | `backend/app/services/models_service.py` | `get_models_status()` — reads `OllamaAvailability` + settings; no 503 on this endpoint. |
| 15 | `backend/app/api/routes/documents.py` | Thin `POST/GET/DELETE` handlers under `/api/v1` with `response_model` and 50MB PDF validation. |
| 16 | `backend/app/api/routes/chat.py` | Thin `POST /chat/{session_id}` returning `StreamingResponse(text/event-stream)`. |
| 17 | `backend/app/api/routes/models.py` | Thin `GET /models/status` → `models_service.get_models_status()`. |
| 18 | `backend/tests/conftest.py` | Shared fixtures: temp dirs, **`mock_embedding_service`**, **`mock_llm_stream`**, **`mock_ollama_availability`**, `sample.pdf`. |
| 19 | `backend/tests/fixtures/sample.pdf` | Real 2+ page PDF (500+ words) — generated by conftest/script before tests run. |
| 20 | `backend/tests/test_pdf_parser.py` | Unit tests: chunk count ≥2, metadata fields, empty/corrupt PDF → `ValueError`. |
| 21 | `backend/tests/test_rag.py` | Unit tests: memory, `astream_response` — **all Ollama/provider calls mocked via pytest-mock**. |
| 22 | `backend/tests/test_documents_api.py` | Integration: upload/list/delete — mocked providers + **503 when Ollama marked offline**. |
| 23 | `backend/tests/test_models_status.py` | **`GET /api/v1/models/status`** with mocked **online** and **offline** Ollama states. |
| 24 | `backend/scripts/generate_sample_pdf.py` | One-shot script to (re)generate `tests/fixtures/sample.pdf` for local dev. |
| 25 | `docs/setup.md` | Local Ollama install, `ollama pull`, `ollama serve`, verify `OLLAMA_BASE_URL`. |

**Total new: 24 implementation files + 1 script + 1 doc.**

### Provider abstraction (`providers.py`)

```python
from abc import ABC, abstractmethod
from typing import List, AsyncGenerator

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]: ...

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]: ...

class BaseChatProvider(ABC):
    @abstractmethod
    async def astream(self, messages) -> AsyncGenerator[str, None]: ...
```

**Rules:**

- `document_service` / `chat_service` / route modules import **`BaseEmbeddingProvider`**, **`BaseChatProvider`**, or factory getters only.
- Ollama concrete classes: `LocalEmbeddingService`, `OllamaChatProvider` in `app/core/`.
- Swapping providers later = new class + `provider_factory.py` change; **zero route changes**.

### `OllamaAvailability` (in `providers.py`)

Shared singleton (also on `app.state.ollama_availability`):

| Method | Behavior |
|--------|----------|
| `async ping_startup()` | `GET {OLLAMA_BASE_URL}/api/tags` via `httpx` (short timeout); on failure **log warning**, set `online=False`; **never raise**. |
| `async refresh()` | Re-ping `/api/tags` (used by status endpoint and before AI requests). |
| `async require_available()` | If offline or required models missing → `HTTPException(503, detail=OLLAMA_UNAVAILABLE_DETAIL)`. |
| `get_status_snapshot()` | Returns cached `online`, configured model names, `models_ready` bool. |

**`models_ready`:** `true` only when Ollama is online **and** `/api/tags` includes both `OLLAMA_CHAT_MODEL` and `OLLAMA_EMBED_MODEL`.

**Standard 503 `detail` string** (single constant, used everywhere):

```
Local AI models unavailable. Start Ollama with: ollama serve
Then pull models:
ollama pull llama3
ollama pull nomic-embed-text
```

(Model names in the message use **configured** values from settings, not hardcoded literals in routes.)

---

## Graceful degradation

### Startup (`main.py` lifespan)

1. Create `uploads/` and `chroma_db/` if missing (existing plan).
2. Instantiate `OllamaAvailability(settings)` → `await ping_startup()`.
3. If unreachable: **log warning** (e.g. `"Ollama unreachable at startup; AI endpoints will return 503 until available"`).
4. **Do not** raise, block, or fail application startup.
5. Attach checker to `app.state` for DI in services.

### Request time (AI endpoints only)

Before processing in **upload** (embeddings) and **chat** (LLM):

- Call `await ollama_availability.require_available()` (fresh ping or TTL-cached refresh, e.g. 30s).
- If unavailable → immediate **HTTP 503** with standard `detail` JSON above.

**Not gated by Ollama:** `GET /health`, `GET /api/v1/models/status`, `GET /api/v1/documents`, `DELETE /api/v1/documents/{doc_id}` (no embedding/chat).

### `GET /api/v1/models/status`

**Always returns 200** (diagnostic endpoint, not a health gate).

Response model `ModelsStatusResponse`:

```json
{
  "ollama": "online",
  "chat_model": "llama3",
  "embed_model": "nomic-embed-text",
  "models_ready": true
}
```

| Field | Values | Source |
|-------|--------|--------|
| `ollama` | `"online"` \| `"offline"` | Latest ping to `/api/tags` |
| `chat_model` | string | `settings.ollama_chat_model` |
| `embed_model` | string | `settings.ollama_embed_model` |
| `models_ready` | `true` \| `false` | online **and** both models present in tags |

Implemented in `models_service.get_models_status()`; thin route in `api/routes/models.py`.

---

## Dependencies to append (`requirements.txt`)

Pinned for **Python 3.11** (Docker) and **3.14** (local). **Explicitly excluded:** `openai`, `langchain-openai`.

```
# Phase 2 — RAG (append after Phase 1 pins)
langchain==0.3.14
langchain-core==0.3.29
langchain-community==0.3.14
langchain-text-splitters==0.3.5
langchain-chroma==0.2.0
chromadb==0.5.23
pymupdf==1.25.2
ollama==0.4.7
python-multipart>=0.0.9
sse-starlette>=2.1.0
aiofiles>=23.2.1
# Test / fixture generation
fpdf2==2.8.2
pytest-mock==3.14.0
```

(Exact upper pins for `python-multipart`, `sse-starlette`, `aiofiles` resolved at implementation time, e.g. `0.0.20`, `2.2.1`, `24.1.0`.)

**LangChain / provider API choices (non-deprecated):**

| Use | Avoid |
|-----|--------|
| `langchain_core.documents.Document` | Old `langchain.schema.Document` |
| `langchain_text_splitters.RecursiveCharacterTextSplitter` | `langchain.text_splitter` |
| `langchain_community.embeddings.OllamaEmbeddings` | `OpenAIEmbeddings`, `langchain_openai` |
| `langchain_community.chat_models.ChatOllama` | `ChatOpenAI`, any `openai` SDK |
| `langchain.chains.history_aware_retriever.create_history_aware_retriever` | `ConversationalRetrievalChain` |
| `langchain.chains.combine_documents.create_stuff_documents_chain` | `load_qa_chain` |
| `langchain.chains.retrieval.create_retrieval_chain` | `RetrievalQA` |
| `langchain_chroma.Chroma` | Deprecated community Chroma paths |
| `langchain.memory.ConversationBufferWindowMemory` | `ConversationChain` |
| `ollama` Python client (health checks / optional) | Cloud embedding/chat APIs |

---

## New environment variables

| Variable | Purpose | `.env.example` default |
|----------|---------|------------------------|
| `OLLAMA_BASE_URL` | Ollama HTTP API base | `http://localhost:11434` |
| `OLLAMA_CHAT_MODEL` | Chat model name (not hardcoded in routes) | `llama3` |
| `OLLAMA_EMBED_MODEL` | Embedding model name | `nomic-embed-text` |
| `CHROMA_DB_PATH` | Chroma persistence root | `./chroma_db` |
| `UPLOADS_DIR` | Stored PDF files | `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | Upload limit | `50` |

`config.py` adds typed fields + `max_upload_size_bytes: int` computed property. **No API keys.**

**Docker manual testing:** container may need `OLLAMA_BASE_URL=http://host.docker.internal:11434` to reach Ollama on the host.

---

## API contracts (schemas)

### `POST /api/v1/upload` → `UploadResponse`

```json
{
  "doc_id": "uuid-string",
  "filename": "report.pdf",
  "chunk_count": 12,
  "message": "Document uploaded and indexed successfully"
}
```

### `GET /api/v1/documents` → `list[DocumentInfo]`

```json
[
  {
    "doc_id": "uuid-string",
    "filename": "report.pdf",
    "chunk_count": 12,
    "created_at": "2026-05-17T12:00:00Z"
  }
]
```

(`created_at` from filesystem mtime or Chroma metadata — implementation picks one consistent source.)

### `DELETE /api/v1/documents/{doc_id}` → `DeleteResponse`

```json
{
  "doc_id": "uuid-string",
  "deleted": true,
  "message": "Document and index removed"
}
```

### `GET /api/v1/models/status` → `ModelsStatusResponse`

Always **HTTP 200** (even when Ollama is offline).

```json
{
  "ollama": "online",
  "chat_model": "llama3",
  "embed_model": "nomic-embed-text",
  "models_ready": true
}
```

### AI endpoints — HTTP 503 when Ollama unavailable

`POST /api/v1/upload`, `POST /api/v1/chat/{session_id}`:

```json
{
  "detail": "Local AI models unavailable. Start Ollama with: ollama serve\nThen pull models:\nollama pull llama3\nollama pull nomic-embed-text"
}
```

(Exact model names in `detail` match `OLLAMA_CHAT_MODEL` / `OLLAMA_EMBED_MODEL` from settings.)

### `POST /api/v1/chat/{session_id}` — SSE body (`ChatRequest`)

Request JSON: `{ "question": "...", "doc_id": "..." }`

Per-token event:

```
data: {"token":"Hello","done":false}

```

Final event:

```
data: {"token":"","done":true,"sources":[{"page_number":1,"source_filename":"x.pdf","content":"..."}]}

```

---

## Test mocking strategy (no live Ollama in pytest)

**Confirmed approach:** `pytest` runs **fully offline** — no `ollama serve`, no pulled models, no HTTP to `OLLAMA_BASE_URL`. Only **manual** Swagger/Docker verification uses a live Ollama server.

| Test file | What is mocked | What is real |
|-----------|----------------|--------------|
| `test_pdf_parser.py` | Nothing external | PyMuPDF + splitter on `sample.pdf` / temp files |
| `test_rag.py` | `BaseEmbeddingProvider`, `BaseChatProvider`, `ChatOllama` / `OllamaEmbeddings`, chain `astream` via pytest-mock | In-process `MemoryManager`, temp `CHROMA_DB_PATH` |
| `test_documents_api.py` | `get_embedding_provider` → `mock_embedding_service`; patch `require_available` or mark offline for 503 case | FastAPI app, httpx client, temp uploads, on-disk Chroma |
| `test_models_status.py` | `OllamaAvailability.refresh` / `ping_startup` mocked **online** vs **offline**; optional missing-model tags | httpx client against `/api/v1/models/status` |
| `test_health.py` | `OllamaAvailability` forced offline (autouse) — **`/health` must still 200** | ASGI app only |

**Implementation details:**

- `tests/conftest.py` provides:
  - `mock_settings` — Ollama URL + model names + temp `uploads` / `chroma` paths
  - `mock_embedding_service` — implements `BaseEmbeddingProvider`; deterministic vectors (length **768** for `nomic-embed-text`)
  - `mock_llm_stream` — implements `BaseChatProvider.astream`; yields fake tokens + fake sources for RAG tests
  - `mock_ollama_availability` — controllable `online` / `models_ready`; `require_available()` no-op when tests expect success
- Autouse or per-test patches via **pytest-mock** at factory boundaries, e.g.:
  - `mocker.patch("app.core.provider_factory.get_embedding_provider", return_value=mock_embedding_service)`
  - `mocker.patch("app.core.provider_factory.get_chat_provider", return_value=mock_chat_provider)`
- **No** skip-if-Ollama-unavailable markers; **no** live model calls in CI/Docker pytest.
- Post-test repo check: `grep -ri "openai" backend/` → zero matches.

---

## Module design summary

### `pdf_parser.py`

- `async def parse_pdf(file_path: Path, source_filename: str) -> list[Document]`
- `asyncio.to_thread` around fitz open + text extract + splitter
- Splitter: `chunk_size=1000`, `chunk_overlap=200`, separators `["\n\n", "\n", ". ", " ", ""]`
- Metadata: `page_number`, `source_filename`, `chunk_index`
- `ValueError` if no extractable text or corrupt file

### `providers.py` + `provider_factory.py`

- ABCs as specified above; **`OllamaAvailability`** with startup ping + `require_available()` + shared 503 detail constant.
- Factory returns `LocalEmbeddingService` + `OllamaChatProvider` from `Settings`.

### `embeddings.py`

- `LocalEmbeddingService(BaseEmbeddingProvider)` wraps `OllamaEmbeddings` from `langchain_community.embeddings`
- Model: `settings.ollama_embed_model` (default `nomic-embed-text`)
- Base URL: `settings.ollama_base_url`
- `embed_documents` / `embed_query`: call `require_available()` first; then `asyncio.to_thread` for sync LangChain calls
- On runtime failure after availability check: log warning, raise `HTTPException(503, detail=OLLAMA_UNAVAILABLE_DETAIL)`

### `ollama_chat.py`

- `OllamaChatProvider(BaseChatProvider)` wraps `ChatOllama` (`temperature=0`, `streaming=True`)
- Model: `settings.ollama_chat_model` (default `llama3`); base URL from settings
- `astream(messages)`: `require_available()` first; yields string tokens; on failure: log warning, **503** with standard detail — **no fallback model**

### `models_service.py`

- `async def get_models_status(ollama: OllamaAvailability, settings: Settings) -> ModelsStatusResponse`
- Calls `await ollama.refresh()` (or uses recent cache) and maps to response fields
- Never raises 503 — informational only

### `vector_store.py`

- `ChromaVectorStore(settings)` with `PersistentClient` path from settings
- Collection name = `doc_id` (sanitized)
- `add_documents`, `similarity_search` (MMR k=5 fetch_k=20), `delete_collection`, `list_collections`
- Returns LangChain `Document` objects from search for source citation

### `memory.py`

- In-memory dict `session_id → (memory, last_accessed)`
- `ConversationBufferWindowMemory(k=10, return_messages=True)`
- Background/async sweep or check-on-access: expire sessions after **2 hours** inactivity
- `clear_memory`, `list_sessions`

### `rag_pipeline.py`

- `RAGPipeline` accepts `BaseChatProvider` (injected from factory) — **no** `ChatOllama` import in services/routes
- Dict `session_id → chain` (built lazily, invalidated on memory clear/expiry)
- Build retriever from `ChromaVectorStore` → history-aware retriever → stuff chain → `create_retrieval_chain`; chat leg streams via `BaseChatProvider.astream`
- `async def astream_response(session_id, question, doc_id) -> AsyncGenerator[dict, None]` yielding `{"token": str}` then `{"token": "", "done": True, "sources": [...]}`
- Client disconnect: handle `asyncio.CancelledError` gracefully
- Model unavailable: propagate 503 from chat provider (no silent fallback)

### `document_service.py`

- Constructor/factory injects `BaseEmbeddingProvider` + `OllamaAvailability`
- `ingest_upload`: **`await ollama.require_available()`** first, then stream PDF → parser → embed → vector store
- `async def list_documents() -> list[DocumentInfo]`
- `async def delete_document(doc_id: str) -> DeleteResponse`
- Raises `HTTPException` with clear `detail` on validation/storage failures

### `chat_service.py`

- `stream_chat`: **`await ollama.require_available()`** first, then SSE formatting via `RAGPipeline`

### `main.py` (lifespan update)

```text
on startup:
  mkdir uploads, chroma_db
  ollama = OllamaAvailability(settings)
  await ollama.ping_startup()   # never raises
  app.state.ollama_availability = ollama
on shutdown:
  (optional) close httpx client if held on OllamaAvailability
```

### `api/routes/models.py`

- `GET /models/status`, `response_model=ModelsStatusResponse`, delegates to `models_service`

---

## Exact creation order (with dependency reasoning)

Grouped by your **5 execution stages**. Within each stage, order matters for imports.

### Stage 1 — Foundation

```
1.  backend/requirements.txt          # append Phase 2 pins (nothing imports yet)
2.  backend/.env.example              # new env vars documented
3.  backend/app/config.py             # new settings fields (schemas depend on types)
4.  backend/app/schemas/document.py   # no upstream app deps
5.  backend/app/schemas/chat.py
6.  backend/app/schemas/models.py
7.  backend/app/schemas/__init__.py   # re-exports
```

### Stage 2 — Core AI layer

```
8.  backend/app/core/providers.py         # ABCs + OllamaAvailability (ping logic)
9.  backend/app/core/pdf_parser.py
10. backend/app/core/embeddings.py
11. backend/app/core/ollama_chat.py
12. backend/app/core/provider_factory.py
13. backend/app/core/vector_store.py
14. backend/app/core/memory.py
```

### Stage 3 — Services + routes

```
11. backend/app/services/document_service.py  # parser + embeddings + vector_store
12. backend/app/services/chat_service.py      # depends on rag_pipeline interface (stub import OK if rag built next; implement chat_service after rag_pipeline OR define protocol — plan: build rag_pipeline before chat_service in Stage 4, so reorder: document_service first, then rag, then chat_service, then routes)

**Adjusted Stage 3/4 order (dependency-correct):**

15. backend/app/core/rag_pipeline.py
16. backend/app/services/models_service.py   # status logic (depends on OllamaAvailability)
17. backend/app/services/document_service.py
18. backend/app/services/chat_service.py
19. backend/app/api/routes/models.py
20. backend/app/api/routes/documents.py
21. backend/app/api/routes/chat.py
```

### Stage 4 — App wiring + docs

```
22. backend/app/api/__init__.py       # mount v1 routers incl. models
23. backend/app/main.py              # lifespan: mkdir + non-blocking Ollama ping
24. docs/setup.md
```

### Stage 5 — Tests + fixture

```
25. backend/scripts/generate_sample_pdf.py
26. backend/tests/conftest.py
27. backend/tests/fixtures/sample.pdf
28. backend/tests/test_pdf_parser.py
29. backend/tests/test_rag.py
30. backend/tests/test_models_status.py    # online + offline mocks
31. backend/tests/test_documents_api.py
```

**Run tests after each stage:**

| After stage | Command |
|-------------|---------|
| 1 | `pytest tests/test_health.py` (regression) |
| 2 | `pytest tests/test_pdf_parser.py` |
| 3–4 | `pytest tests/test_rag.py tests/test_models_status.py tests/test_health.py` |
| 5 | Full `pytest` + Docker verification |

---

## Consolidated linear order (single checklist)

```
 1. requirements.txt
 2. .env.example
 3. config.py
 4. schemas/document.py
 5. schemas/chat.py
 6. schemas/models.py
 7. schemas/__init__.py
 8. core/providers.py              # ABCs + OllamaAvailability
 9. core/pdf_parser.py
10. core/embeddings.py
11. core/ollama_chat.py
12. core/provider_factory.py
13. core/vector_store.py
14. core/memory.py
15. core/rag_pipeline.py
16. services/models_service.py
17. services/document_service.py
18. services/chat_service.py
19. api/routes/models.py
20. api/routes/documents.py
21. api/routes/chat.py
22. api/__init__.py
23. main.py                        # lifespan: mkdir + Ollama ping (no crash)
24. docs/setup.md
25. scripts/generate_sample_pdf.py
26. tests/conftest.py
27. tests/fixtures/sample.pdf
28. tests/test_pdf_parser.py
29. tests/test_rag.py
30. tests/test_models_status.py
31. tests/test_documents_api.py
```

---

## Post-implementation verification

### Automated (pytest — no Ollama required)

| # | Check |
|---|--------|
| 1 | `pytest` — all tests pass with **zero** live Ollama/model calls |
| 2 | `grep -ri "openai" backend/` → **zero** results |
| 3 | `GET /health` → 200 with Ollama **offline** (mocked) |
| 4 | `GET /api/v1/models/status` → 200, `ollama: offline` when mocked offline |
| 5 | Upload/chat return **503** with standard `detail` when Ollama mocked offline |

### Manual (local Ollama — see `docs/setup.md`)

Prerequisites: `ollama serve`, `ollama pull llama3`, `ollama pull nomic-embed-text`.

| # | Check |
|---|--------|
| 1 | Ollama responds at `OLLAMA_BASE_URL` (e.g. `GET http://localhost:11434`) |
| 2 | `nomic-embed-text` produces embeddings locally (upload flow) |
| 3 | PDF upload → vectors in ChromaDB, `chunk_count > 0` |
| 4 | `POST /api/v1/chat/{session_id}` → SSE streams tokens from `llama3` |
| 5 | Final SSE event has `done: true` and `sources` |
| 6 | `docker build` + `docker run` (optional; map `OLLAMA_BASE_URL` to host) |
| 7 | `GET /docs` lists all `/api/v1` endpoints incl. `/models/status` |
| 8 | Start app **without** Ollama → startup succeeds; `/health` 200; `/models/status` shows `offline` |
| 9 | Start Ollama + pull models → `/models/status` shows `models_ready: true`; upload + chat work |

Fix all failures before sign-off.

---

## Deliverables (after implementation)

1. Final `backend/` file tree  
2. Full `requirements.txt` with new pins  
3. Docker build (last 10 lines)  
4. Docker run + `/health` JSON  
5. Example `/upload` response JSON  
6. Example SSE output (5 tokens + final sources)  
7. Full pytest summary  

---

## Out of scope (Phase 2)

- Frontend  
- Authentication (Phase 3)  
- PostgreSQL / Redis (Phase 4)  
- Changes to `/health` behavior or Phase 1 health modules  
- OpenAI or any paid/cloud LLM API  

---

## Do not (Phase 2)

- Use OpenAI or any paid API  
- Hardcode model names in routes or services (use `Settings` only)  
- Silently swallow model errors or fall back to another model  
- Break Phase 1 `/health` or make `/health` depend on Ollama  
- **Crash startup** if Ollama is offline or `/api/tags` fails  
- Write code before plan approval  

---

## Documentation (`docs/setup.md`)

```markdown
# Local Model Setup

1. Install Ollama: https://ollama.com/download
2. Pull required models:
   ollama pull llama3
   ollama pull nomic-embed-text
3. Start Ollama server:
   ollama serve
4. Verify at: http://localhost:11434
```

---

## Phase 2 approval

Reply **approve** (or note changes). After approval, implementation follows the **5 stages** above with pytest between stages. **pytest = mocked Ollama only**; live Ollama = manual verification only.

---

# Phase 3 — JWT Authentication + Multi-User Architecture: Implementation Plan

**Status:** Awaiting approval — no Phase 3 code will be written until you approve this section.

**Scope:** SQLite + SQLAlchemy + Alembic, JWT access/refresh tokens, per-user document ownership, scoped chat memory. **Free stack only** — no PostgreSQL, no cloud APIs, Ollama stays local, all Phase 2 RAG behavior preserved.

**Prerequisite:** Phase 2 verified (upload, Chroma, SSE, 12 pytest, Docker E2E).

---

## Phase 3 architecture notes

| Constraint | How we satisfy it |
|------------|-------------------|
| Single DI entry point | `get_current_user` added to **`app/api/deps.py` only** — no parallel auth middleware or second DI module |
| Document ownership | `DocumentMeta` in SQLite replaces `documents_index.json`; all list/delete/chat/upload scoped by `user_id` |
| Chat memory isolation | Internal session key: `f"{user_id}:{session_id}"` in `ChatService` / `MemoryManager` usage |
| Refresh without access token | `POST /auth/refresh` accepts body `{ refresh_token }` only; rotation revokes old row |
| Test DB isolation | Each DB test uses `sqlite:///{tmp_path}/test.db`; tables created/dropped per test — **never shared** |
| Phase 2 tests | All 12 existing tests updated where needed (Bearer mock / override `get_current_user`) and must keep passing |
| Ollama offline in pytest | Unchanged — mock `OllamaAvailability`; no live model calls |
| Docker persistence | `data/` volume for SQLite; `DATABASE_URL=sqlite:///./data/app.db`; document both PowerShell and Bash run commands |

### `auth/dependencies.py` — not created

The prompt lists `app/auth/dependencies.py`, but also forbids a second DI system. **Resolution:** implement `oauth2_scheme` + `get_current_user` in **`app/api/deps.py`**; `app/auth/` contains only `security.py` (hash/JWT helpers) and `__init__.py`.

---

## Public vs protected routes (after Phase 3)

| Access | Routes |
|--------|--------|
| **Public** | `GET /health`, `GET /api/v1/models/status`, `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /docs`, `GET /openapi.json` |
| **Protected** (Bearer) | `GET /api/v1/auth/me`, `POST /api/v1/upload`, `GET /api/v1/documents`, `DELETE /api/v1/documents/{doc_id}`, `POST /api/v1/chat/{session_id}` |

---

## SQLite schema summary

### `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | `uuid4` default |
| `email` | String | unique, indexed, lowercase+strip on write |
| `hashed_password` | String | bcrypt via passlib |
| `is_active` | Boolean | default `True` |
| `created_at` | DateTime | UTC, server default |

### `refresh_tokens`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | |
| `token` | String | unique, indexed, opaque random |
| `user_id` | UUID FK → `users.id` | `ON DELETE CASCADE` |
| `expires_at` | DateTime | now + `REFRESH_TOKEN_EXPIRE_DAYS` |
| `created_at` | DateTime | |
| `is_revoked` | Boolean | default `False`; set `True` on refresh rotation |

### `document_meta`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | |
| `doc_id` | String | unique, indexed; matches Chroma collection key |
| `user_id` | UUID FK → `users.id` | `ON DELETE CASCADE` |
| `filename` | String | |
| `chunk_count` | Integer | |
| `created_at` | DateTime | |

**Removed in Phase 3:** `uploads/documents_index.json` — metadata moves to `document_meta` only.

---

## JWT flow (register → login → use → refresh)

```
1. POST /auth/register  → creates User (password hashed)
2. POST /auth/login     → access_token (15m) + refresh_token (7d, stored in DB)
3. Protected calls      → Authorization: Bearer <access_token>
                          deps.get_current_user decodes JWT → loads User → 401 variants
4. POST /auth/refresh   → body: { refresh_token } (no Bearer required)
                          validates row (exists, not revoked, not expired)
                          revokes old token → issues new access + new refresh
5. Access expired       → client uses refresh; if refresh invalid → re-login
```

**401 detail strings (exact):** `Not authenticated` | `Invalid token` | `Token expired` | `Token revoked`

---

## Every new file to create (18 files)

| # | File | What it does (one sentence) |
|---|------|-----------------------------|
| 1 | `backend/alembic.ini` | Alembic project config pointing at `app.db` models and `versions/`. |
| 2 | `backend/alembic/env.py` | Alembic env: imports `Base`, uses `DATABASE_URL` from settings. |
| 3 | `backend/alembic/script.py.mako` | Migration template (standard Alembic). |
| 4 | `backend/alembic/versions/0001_initial.py` | Creates `users`, `refresh_tokens`, `document_meta`. |
| 5 | `backend/app/db/__init__.py` | Package exports `get_db`, `Base`, engine helpers. |
| 6 | `backend/app/db/base.py` | SQLAlchemy `DeclarativeBase` for all models. |
| 7 | `backend/app/db/database.py` | Engine, `SessionLocal`, `get_db()` dependency generator. |
| 8 | `backend/app/models/user.py` | `User` ORM model. |
| 9 | `backend/app/models/token.py` | `RefreshToken` ORM model. |
| 10 | `backend/app/models/document_meta.py` | `DocumentMeta` ORM model. |
| 11 | `backend/app/auth/__init__.py` | Auth package marker. |
| 12 | `backend/app/auth/security.py` | bcrypt hash/verify, JWT encode/decode, refresh token generation. |
| 13 | `backend/app/schemas/auth.py` | `RegisterRequest`, `LoginRequest`, `RefreshRequest`, `TokenResponse`, `UserResponse`. |
| 14 | `backend/app/services/auth_service.py` | `register`, `login`, `refresh`, `get_user_by_id` business logic. |
| 15 | `backend/app/api/routes/auth.py` | Four auth endpoints with `response_model` on each. |
| 16 | `backend/tests/test_auth.py` | All 16 auth/ownership test cases (see Testing). |
| 17 | `backend/pytest.ini` | (modify) ensure asyncio + test paths unchanged. |
| 18 | `README.md` (repo root) | Docker run commands (PowerShell + Bash) + auth overview. |

**Note:** `app/models/__init__.py` updated to export ORM models (modify, not counted as new).

---

## Phase 2 files to modify (exact changes)

| File | Exact changes |
|------|----------------|
| `backend/requirements.txt` | Append: `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`, `sqlalchemy==2.0.36`, `alembic==1.14.0`, `bcrypt==4.0.1`, `email-validator` (for `EmailStr` in schemas). |
| `backend/.env.example` | Add `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `DATABASE_URL`. |
| `backend/app/config.py` | Add auth + DB settings fields; property for SQLite path / `data/` parent. |
| `backend/app/main.py` | Lifespan: `mkdir data/`, run `alembic upgrade head`, keep Ollama ping + uploads/chroma mkdir; on shutdown close DB engine if needed. |
| `backend/app/api/deps.py` | Add `oauth2_scheme`, `get_db` usage, **`get_current_user`**; keep existing `get_*` deps unchanged. |
| `backend/app/api/__init__.py` | Register `auth.router` under prefix `/api/v1/auth`. |
| `backend/app/api/routes/documents.py` | Add `current_user: User = Depends(get_current_user)` on upload/list/delete; pass `user` to service. |
| `backend/app/api/routes/chat.py` | Add `current_user` dependency; pass `user` + verify `doc_id` ownership before stream. |
| `backend/app/services/document_service.py` | Accept `Session` + `user_id`; **replace JSON index** with `DocumentMeta` CRUD; ownership checks → 403. |
| `backend/app/services/chat_service.py` | Accept `user_id`; scope memory key `f"{user_id}:{session_id}"`; verify doc ownership before RAG. |
| `backend/app/schemas/__init__.py` | Export auth schemas. |
| `backend/Dockerfile` | `COPY alembic.ini alembic/ ./`; ensure `data/` writable; CMD unchanged. |
| `backend/tests/conftest.py` | Add `db_session` fixture (`tmp_path` SQLite, create/drop tables); `auth_headers` fixture; override `get_db` + `get_current_user` for API tests; keep Ollama mocks. |
| `backend/tests/test_documents_api.py` | Register/login or override user; send Bearer on protected routes; adjust for SQLite metadata. |
| `docs/setup.md` | Add auth env vars, `SECRET_KEY` generation, Docker volume mounts (PowerShell + Bash). |
| `.gitignore` | Add `data/`, `*.db`, `backend/data/`. |

**Not modified:** `health.py`, `models.py` (routes), `rag_pipeline.py`, `vector_store.py`, `providers.py`, core PDF/Ollama logic (except memory key passed from chat service).

---

## Auth API contracts

### `POST /api/v1/auth/register` → `UserResponse`

```json
{ "user_id": "uuid", "email": "user@example.com", "created_at": "2026-05-20T12:00:00Z" }
```

- 400: email already registered  
- 422: invalid email / password &lt; 8 chars  

### `POST /api/v1/auth/login` → `TokenResponse`

```json
{
  "access_token": "eyJ...",
  "refresh_token": "opaque-...",
  "token_type": "bearer"
}
```

### `POST /api/v1/auth/refresh` → `TokenResponse`

Request: `{ "refresh_token": "..." }` — **no** `Authorization` header.

### `GET /api/v1/auth/me` → `UserResponse`

Requires Bearer access token.

### Protected upload (example)

```http
POST /api/v1/upload
Authorization: Bearer eyJ...
Content-Type: multipart/form-data
```

Response unchanged from Phase 2 `UploadResponse`; plus `DocumentMeta` row with `user_id`.

---

## Testing requirements

### Offline rule

- No live Ollama; no shared SQLite file between tests.  
- `test_auth.py` uses in-memory/temp-file DB per test via `tmp_path`.  
- Phase 2 tests: mock Ollama + provide valid Bearer or `app.dependency_overrides[get_current_user]`.

### `test_auth.py` cases (16)

| # | Test |
|---|------|
| 1 | register new user → 200 + `UserResponse` |
| 2 | register duplicate email → 400 |
| 3 | register weak password (&lt; 8) → 422 |
| 4 | login valid → 200 + both tokens |
| 5 | login wrong password → 401 |
| 6 | login unknown email → 401 |
| 7 | `/auth/me` valid token → 200 |
| 8 | `/auth/me` no token → 401 `Not authenticated` |
| 9 | `/auth/me` expired token → 401 `Token expired` |
| 10 | refresh valid → 200 + new tokens; old refresh revoked in DB |
| 11 | refresh revoked token → 401 `Token revoked` |
| 12 | upload creates `DocumentMeta` with correct `user_id` |
| 13 | user A cannot access user B `doc_id` via chat → 403 |
| 14 | user A cannot delete user B doc → 403 |
| 15 | user A list documents excludes user B rows |
| 16 | invalid access token → 401 `Invalid token` |

### Phase 2 regression (must stay green)

| Suite | Tests |
|-------|-------|
| `test_health.py` | 2 |
| `test_pdf_parser.py` | 3 |
| `test_rag.py` | 2 |
| `test_models_status.py` | 3 |
| `test_documents_api.py` | 2 (updated for auth) |
| **Phase 3** | `test_auth.py` | 16 |
| **Total target** | **28 passed, 0 failed** |

---

## Implementation stages (7 stages + pytest gates)

### Stage 1 — Database foundation

```
1.  requirements.txt          # append SQLAlchemy, Alembic, jose, passlib, bcrypt, email-validator
2.  .env.example              # SECRET_KEY, DATABASE_URL, token expiry vars
3.  app/config.py             # new settings
4.  app/db/base.py
5.  app/db/database.py
6.  app/db/__init__.py
7.  app/models/user.py
8.  app/models/token.py
9.  app/models/document_meta.py
10. app/models/__init__.py    # export ORM models
11. alembic.ini
12. alembic/env.py
13. alembic/script.py.mako
14. alembic/versions/0001_initial.py
15. tests/conftest.py         # add db_session fixture (minimal)
```

**Pytest gate:** `pytest tests/test_health.py tests/test_pdf_parser.py tests/test_rag.py tests/test_models_status.py -q` → **10 passed** (documents API may skip until Stage 5 or use overrides).

---

### Stage 2 — Auth core

```
16. app/auth/__init__.py
17. app/auth/security.py      # passlib + python-jose
18. app/schemas/auth.py
19. app/services/auth_service.py
```

**Pytest gate:** Phase 2 non-DB tests still pass; optional unit tests on `security.py` hash/JWT roundtrip inside `test_auth.py` stubs.

---

### Stage 3 — Auth routes

```
20. app/api/routes/auth.py
21. app/api/__init__.py        # mount /api/v1/auth
22. app/schemas/__init__.py
```

**Pytest gate:** `pytest tests/test_auth.py -k "register or login"` → register/login tests pass.

---

### Stage 4 — Dependency injection

```
23. app/api/deps.py            # oauth2_scheme + get_current_user + get_db wiring
```

**Pytest gate:** `pytest tests/test_auth.py -k "me or token"` → me + token validation tests pass.

---

### Stage 5 — Ownership enforcement

```
24. app/services/document_service.py   # DocumentMeta, remove JSON index
25. app/services/chat_service.py       # user-scoped session + ownership check
26. app/api/routes/documents.py
27. app/api/routes/chat.py
28. tests/test_documents_api.py        # Bearer + two-user isolation
```

**Pytest gate:** `pytest tests/test_auth.py tests/test_documents_api.py -q` → ownership + documents pass.

---

### Stage 6 — App wiring

```
29. app/main.py               # lifespan: data/, alembic upgrade head, DB engine
30. Dockerfile                # COPY alembic + alembic.ini
31. .gitignore                # data/
32. docs/setup.md             # auth + Docker volumes
33. README.md                 # PowerShell + Bash docker run
```

**Pytest gate:** `pytest -q` → **28 passed, 0 failed**.

---

### Stage 7 — Full tests + Docker

```
34. tests/test_auth.py        # complete all 16 cases
35. Verify grep no hardcoded SECRET_KEY in app code
```

**Commands:**

```powershell
docker build -t ai-doc-assistant-backend .
docker run -p 8000:8000 `
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 `
  -v "${PWD}/data:/app/data" `
  --env-file .env `
  ai-doc-assistant-backend
```

Manual flow: register → login → upload with Bearer → list docs → chat SSE → refresh tokens.

**Pytest gate:** full suite + Docker health 200.

---

## Consolidated linear order (34 steps)

```
 1. requirements.txt
 2. .env.example
 3. config.py
 4. db/base.py
 5. db/database.py
 6. db/__init__.py
 7. models/user.py
 8. models/token.py
 9. models/document_meta.py
10. models/__init__.py
11. alembic.ini
12. alembic/env.py
13. alembic/script.py.mako
14. alembic/versions/0001_initial.py
15. tests/conftest.py (db fixture)
16. auth/__init__.py
17. auth/security.py
18. schemas/auth.py
19. services/auth_service.py
20. api/routes/auth.py
21. api/__init__.py
22. schemas/__init__.py
23. api/deps.py (get_current_user)
24. services/document_service.py
25. services/chat_service.py
26. api/routes/documents.py
27. api/routes/chat.py
28. tests/test_documents_api.py
29. main.py
30. Dockerfile
31. .gitignore
32. docs/setup.md
33. README.md
34. tests/test_auth.py
```

---

## Post-implementation verification

| # | Check |
|---|--------|
| 1 | `pytest` → 28 passed, 0 failed |
| 2 | `grep -ri "openai" backend/` → zero |
| 3 | No hardcoded `SECRET_KEY` in source |
| 4 | `/health` + `/models/status` work without auth |
| 5 | Register + login + me + refresh flow |
| 6 | Upload/list/delete/chat require Bearer |
| 7 | Cross-user doc access → 403 |
| 8 | Docker build + run with `data/` volume persists users |
| 9 | Phase 2 RAG still works with Ollama + pulled models |

---

## Final deliverables (after implementation)

1. Final `backend/` file tree  
2. New `requirements.txt` lines highlighted  
3. SQLite schema summary (3 tables)  
4. JWT flow explanation  
5. Public vs protected route list  
6. Sample register JSON  
7. Sample login JSON  
8. Sample authenticated upload (headers + response)  
9. Full pytest summary (28 tests)  
10. Docker build + PowerShell run verification  

---

## Out of scope (Phase 3)

- Frontend / UI login screens  
- PostgreSQL / Redis (Phase 4)  
- Logout endpoint (future)  
- Email verification / password reset  
- OAuth social login  
- Paid or cloud services  

---

## Do not (Phase 3)

- Break Phase 2 RAG, Ollama graceful degradation, or `/health`  
- Use PostgreSQL or paid APIs  
- Store plaintext passwords or hardcode `SECRET_KEY`  
- Create a second DI file for `get_current_user` (use `deps.py` only)  
- Share SQLite DB between tests  
- Skip red tests or leave TODO placeholders  
- Write code before plan approval  

---

## Phase 3 approval

Reply **approve** (or note changes). After approval, implementation follows **7 stages** with pytest gates; no stage advance on failures.
