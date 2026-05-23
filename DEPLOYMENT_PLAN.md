# Phase 5 — Production Deployment Plan

**Status:** Awaiting approval — no Phase 5 code will be written until you approve this plan.

**Prerequisite:** Phases 1–4 complete (FastAPI + JWT + RAG + Next.js frontend verified locally).

---

## 1. Deployment architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────┐
│  Vercel (Next.js 14 frontend)       │
│  - Static/SSR app routes            │
│  - NEXT_PUBLIC_API_URL → Railway    │
└─────────────────────────────────────┘
    │ HTTPS  (JSON, multipart upload, SSE)
    ▼
┌─────────────────────────────────────┐
│  Railway (FastAPI backend container)  │
│  - Dockerfile: backend/Dockerfile     │
│  - PORT from Railway                  │
│  - AI_PROVIDER=groq (production)      │
└─────────────────────────────────────┘
    │
    ├── Groq API (chat, free tier) — llama3-8b-8192
    ├── sentence-transformers (embeddings, in-container)
    │
    ▼
┌─────────────────────────────────────┐
│  Railway Volume → /app/data         │
│  ├── app.db          (SQLite)       │
│  ├── uploads/        (PDF files)    │
│  └── chroma_db/      (vectors)      │
└─────────────────────────────────────┘

Local development (unchanged default):
    AI_PROVIDER=ollama → host Ollama (llama3.2:3b + nomic-embed-text)
```

| Environment | Chat | Embeddings | AI availability check |
|-------------|------|------------|------------------------|
| `AI_PROVIDER=ollama` (default) | `OllamaChatProvider` | `LocalEmbeddingService` in `embeddings.py` (Ollama via LangChain) | `OllamaAvailability` → `/api/tags` |
| `AI_PROVIDER=groq` | `GroqChatProvider` | `SentenceTransformerEmbedding` in `sentence_embeddings.py` | `GroqAvailability` → `GROQ_API_KEY` present |

---

## 2. Critical design decisions

### 2.1 Embedding dimension change (must document)

| Provider | Model | Dimensions |
|----------|-------|------------|
| Ollama | `nomic-embed-text` | **768** |
| sentence-transformers | `all-MiniLM-L6-v2` | **384** |

**Risk:** Chroma collections built with Ollama embeddings are **not compatible** with MiniLM embeddings. Switching `AI_PROVIDER` on an existing `/app/data/chroma_db` will cause search/upload errors until documents are re-uploaded.

**Mitigation in plan:**
- Document in README: delete `chroma_db` or re-upload all PDFs after switching providers.
- Optional constant `SENTENCE_EMBED_DIMENSION = 384` in `providers.py` (tests already use `NOMIC_EMBED_DIMENSION = 768` for Ollama mocks).
- Do **not** mix providers against the same Chroma path.

### 2.2 Availability abstraction (required refactor)

Today `DocumentService`, `ChatService`, `RAGPipeline`, and `models_service` depend on `OllamaAvailability.require_available()`.

**Plan:** Introduce a small protocol / base class `AIAvailability` in `providers.py` with:
- `async ping_startup()`
- `async require_available()`
- `get_status_snapshot() -> dict`
- `async close()`

| Class | When |
|-------|------|
| `OllamaAvailability` (existing, implements interface) | `AI_PROVIDER=ollama` |
| `GroqAvailability` (new) | `AI_PROVIDER=groq` — checks `GROQ_API_KEY`, sets `models_ready=True` if key present |

**Why:** Avoid calling Ollama `/api/tags` in production when Ollama does not exist.

**Files touched:** `main.py` lifespan stores `app.state.ai_availability` (keep `ollama_availability` alias for minimal test churn OR update `conftest` + `deps.py` once).

### 2.3 Models status API (backward compatible)

Extend `ModelsStatusResponse` **additively**:

```python
ai_provider: Literal["ollama", "groq"]  # new
ollama: Literal["online", "offline"]     # keep for frontend compat
chat_model: str
embed_model: str
models_ready: bool
```

| Mode | `ai_provider` | `ollama` field | `models_ready` |
|------|---------------|----------------|----------------|
| ollama | `ollama` | real Ollama ping | both models pulled |
| groq | `groq` | `"online"` if Groq ready | `GROQ_API_KEY` set + valid |

**Frontend:** Update `ModelsStatusBadge` to show provider-aware tooltip (Groq vs Ollama). No new npm packages required.

### 2.4 Groq streaming (SSE compatibility)

**Requirement:** Preserve existing SSE format from `chat_service.py`:

```
data: {"token":"...","done":false}

data: {"token":"","done":true,"sources":[...]}

```

**Implementation:** `GroqChatProvider.astream(messages)` uses `groq.AsyncGroq().chat.completions.create(..., stream=True)` and yields **string tokens** only — same contract as `OllamaChatProvider`. No frontend chat rewrite.

**Disconnect:** Handle `asyncio.CancelledError` in `RAGPipeline` (existing) + client abort in Groq stream loop.

### 2.5 sentence-transformers on Railway

**Risk:** Image size (+400–800MB with PyTorch CPU) and cold-start latency (model load ~10–30s first request).

**Mitigations:**
- Lazy-load model singleton on first embed call.
- Dockerfile: `python:3.11-slim` + `apt-get install build-essential` only if needed; prefer pre-built wheels.
- Pin `torch` CPU-only in `requirements.txt` optional extra or documented install line.
- Document Railway free tier RAM (~512MB–1GB) — may need Hobby plan for ST model.

**Alternative considered:** Groq embeddings API — not free/unified; rejected per user spec.

### 2.6 Persistence paths (Railway volume)

All durable data under **`/app/data`**:

| Path | Env var | Purpose |
|------|---------|---------|
| `/app/data/app.db` | `DATABASE_URL=sqlite:////app/data/app.db` | Users, tokens, document_meta |
| `/app/data/uploads/` | `UPLOADS_DIR=/app/data/uploads` | PDF files |
| `/app/data/chroma_db/` | `CHROMA_DB_PATH=/app/data/chroma_db` | Chroma persistence |

**Startup (`main.py` lifespan):** Already mkdirs `data_path`, `uploads_path`, `chroma_path` — verify all three resolve under `/app/data` when env vars set.

**Remove:** Scattered `./chroma_db` and `./uploads` at repo root in production docs (local dev can keep relative paths).

### 2.7 Frontend API safety (no secrets client-side)

| Rule | Implementation |
|------|----------------|
| Only `NEXT_PUBLIC_*` in browser | Already using `NEXT_PUBLIC_API_URL` for upload + SSE |
| Production rewrites | `next.config.mjs` uses `NEXT_PUBLIC_API_URL` when set |
| Error UX | Extend existing inline errors (no new toast library unless you approve): `UploadZone`, `ChatWindow`, `LoginForm`, auth redirect on 401 |
| Backend down | `fetch` failures show connection message; models badge offline |

**No `GROQ_API_KEY` on frontend** — backend only.

### 2.8 Tests must keep passing

- Default `AI_PROVIDER=ollama` in pytest (`conftest.py` unchanged behavior).
- All existing mocks stay valid.
- Add **optional** `tests/test_groq_provider.py` with `pytest-mock` only (no live Groq calls).
- Groq mode verification = manual + docker-compose.prod.yml.

---

## 3. Every file to create or modify

### 3.1 New files

| # | File | Purpose |
|---|------|---------|
| 1 | `backend/app/core/groq_chat.py` | `GroqChatProvider(BaseChatProvider)` — streaming via Groq SDK |
| 2 | `backend/app/core/sentence_embeddings.py` | `SentenceTransformerEmbedding(BaseEmbeddingProvider)` — `all-MiniLM-L6-v2` |
| 3 | `backend/app/core/groq_availability.py` | `GroqAvailability` — key check, status snapshot, `require_available()` |
| 4 | `docker-compose.prod.yml` | Production compose: groq env, single volume `app_data:/app/data` |
| 5 | `railway.json` (repo root) | Railway build/deploy metadata |
| 6 | `backend/Procfile` | `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| 7 | `.env.production.example` (repo root) | Documented production env template |
| 8 | `frontend/.env.production` | Placeholder `NEXT_PUBLIC_API_URL` for local prod builds (git-safe placeholder URL) |
| 8b | `frontend/.env.production.example` | Same template, committed reference for Vercel setup |
| 9 | `backend/tests/test_groq_provider.py` | Mocked Groq provider unit tests (optional gate) |
| 10 | `docs/deployment.md` | Railway + Vercel step-by-step (linked from README) |

### 3.2 Modified files (with rationale)

| File | Why | Risk |
|------|-----|------|
| `backend/app/config.py` | Add `ai_provider`, `groq_api_key`, `groq_chat_model`; helper `is_groq_mode`. **CORS:** `cors_origin_list` already splits comma-separated `CORS_ORIGINS` — no logic change, only production env docs | Low — defaults preserve ollama |
| `backend/app/core/providers.py` | Add `AIAvailability` protocol; `build_groq_unavailable_detail()`; `SENTENCE_EMBED_DIMENSION=384` | Low |
| `backend/app/core/provider_factory.py` | Branch on `settings.ai_provider` for chat + embed + availability factory | Medium — central switch |
| `backend/app/core/ollama_chat.py` | Remove direct `require_available` if moved to factory; keep Ollama logic | Low |
| `backend/app/core/embeddings.py` | Skip Ollama gate when not used (factory only returns in ollama mode) | Low |
| `backend/app/main.py` | Lifespan: `get_ai_availability(settings)`; skip Ollama ping in groq mode; bind `$PORT` via uvicorn CMD | Low |
| `backend/app/api/deps.py` | `get_ai_availability` instead of `get_ollama` (or alias) | Update imports in services |
| `backend/app/services/models_service.py` | Provider-aware status (Groq vs Ollama fields) | Frontend type update |
| `backend/app/schemas/models.py` | Add `ai_provider` field | API additive |
| `backend/app/services/document_service.py` | Use `AIAvailability` type | Typing only |
| `backend/app/services/chat_service.py` | Use `AIAvailability` type | Typing only |
| `backend/app/core/rag_pipeline.py` | Use `AIAvailability` for `require_available` | Typing only |
| `backend/requirements.txt` | Add `groq>=0.4.0`, `sentence-transformers>=2.2.0`, pin CPU `torch` if needed | Image size |
| `backend/Dockerfile` | Multi-stage or optimized install; `CMD` uses `$PORT`; mkdir `/app/data` | Railway compat |
| `backend/.env.example` | Document `AI_PROVIDER`, `GROQ_*`, production paths | Docs |
| `docker-compose.yml` | Keep local dev; add comment pointing to prod compose | None |
| `frontend/next.config.mjs` | Rewrites: dev → `127.0.0.1:8000`; prod → `NEXT_PUBLIC_API_URL` | Must not break local |
| `frontend/lib/types.ts` | Add `ai_provider?` to `ModelsStatus` | TS |
| `frontend/components/dashboard/ModelsStatusBadge.tsx` | Provider-aware labels | UI only |
| `frontend/lib/api.ts` | Clearer errors for 503 / network (upload, chat, stream) | UX |
| `README.md` | Full project + deployment guide | Docs |

### 3.3 Files explicitly NOT changed

| File | Reason |
|------|--------|
| `frontend/app/api/**` | Does not exist; no route handlers |
| `backend/app/core/rag_pipeline.py` chain logic | Only availability type swap |
| `implementation_plan.md` | Historical |
| Phase 1–4 health/auth routes | Unchanged behavior in ollama mode |

### 3.4 No conflicting Next.js API routes

Confirmed: **`frontend/app/api/` does not exist.** Rewrites in `next.config.mjs` remain the proxy mechanism for dev JSON auth calls.

---

## 4. New environment variables

### Backend (`backend/.env` / Railway)

| Variable | Default | Production example |
|----------|---------|-------------------|
| `AI_PROVIDER` | `ollama` | `groq` |
| `GROQ_API_KEY` | `""` | `gsk_...` (from console.groq.com) |
| `GROQ_CHAT_MODEL` | `llama3-8b-8192` | `llama3-8b-8192` |
| `SECRET_KEY` | (dev key) | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `sqlite:///./data/app.db` | `sqlite:////app/data/app.db` |
| `CHROMA_DB_PATH` | `./chroma_db` | `/app/data/chroma_db` |
| `UPLOADS_DIR` | `./uploads` | `/app/data/uploads` |
| `CORS_ORIGINS` | `*` | `https://your-app.vercel.app` |
| `ENVIRONMENT` | `development` | `production` |
| `PORT` | `8000` | Railway injects |

Ollama vars remain for local mode (`OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL`).

### Frontend (Vercel)

| Variable | Example |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.up.railway.app` |

---

## 5. Exact implementation order (after approval)

```
Stage 0 — Git checkpoint
  git add -A && git commit -m "chore: checkpoint before Phase 5 deployment"

Stage 1 — Config + availability abstraction
  1. backend/app/config.py
  2. backend/app/core/providers.py (AIAvailability protocol)
  3. backend/app/core/groq_availability.py

Stage 2 — Providers
  4. backend/app/core/groq_chat.py
  5. backend/app/core/sentence_embeddings.py
  6. backend/app/core/provider_factory.py

Stage 3 — Wire services + status
  7. backend/app/main.py
  8. backend/app/api/deps.py
  9. backend/app/services/models_service.py
  10. backend/app/schemas/models.py
  11. backend/app/services/document_service.py (typing)
  12. backend/app/services/chat_service.py (typing)
  13. backend/app/core/rag_pipeline.py (typing)

Stage 4 — Dependencies + Docker
  14. backend/requirements.txt
  15. backend/Dockerfile
  16. docker-compose.prod.yml
  17. backend/Procfile
  18. railway.json

Stage 5 — Env docs + examples
  19. backend/.env.example
  20. .env.production.example
  21. frontend/.env.production.example

Stage 6 — Frontend production
  22. frontend/next.config.mjs
  23. frontend/lib/types.ts
  24. frontend/components/dashboard/ModelsStatusBadge.tsx
  25. frontend/lib/api.ts (error messages)

Stage 7 — Documentation
  26. docs/deployment.md
  27. README.md

Stage 8 — Tests
  28. backend/tests/test_groq_provider.py (mocked)
  29. Run: cd backend && pytest -q  (must stay green in ollama mode)

Stage 9 — Local verification (groq mode)
  30. Set AI_PROVIDER=groq + GROQ_API_KEY in backend/.env
  31. docker compose -f docker-compose.prod.yml up --build
  32. Upload PDF + chat SSE (no Ollama required)
```

---

## 6. `docker-compose.prod.yml` (planned content)

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      AI_PROVIDER: ${AI_PROVIDER:-groq}
      GROQ_API_KEY: ${GROQ_API_KEY}
      GROQ_CHAT_MODEL: ${GROQ_CHAT_MODEL:-llama3-8b-8192}
      SECRET_KEY: ${SECRET_KEY}
      DATABASE_URL: sqlite:////app/data/app.db
      CHROMA_DB_PATH: /app/data/chroma_db
      UPLOADS_DIR: /app/data/uploads
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000}
      ENVIRONMENT: production
    volumes:
      - app_data:/app/data

volumes:
  app_data:
```

Local groq test: `AI_PROVIDER=groq GROQ_API_KEY=gsk_... docker compose -f docker-compose.prod.yml up --build`

---

## 7. `railway.json` (planned content)

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "backend/Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

**Railway dashboard settings (document in `docs/deployment.md`):**
- Root directory: repository root (Dockerfile path `backend/Dockerfile`)
- Volume mount: `/app/data`
- Health check: `/health`
- Variables: see `.env.production.example`

---

## 8. `frontend/next.config.mjs` (planned behavior)

```javascript
const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const devBackend = "http://127.0.0.1:8000";

const nextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === "production" && apiUrl) {
      return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
    }
    return [{ source: "/api/:path*", destination: `${devBackend}/api/:path*` }];
  },
};
```

**Note:** Upload and SSE already use `NEXT_PUBLIC_API_URL` directly in `lib/api.ts` (bypasses rewrite issues). Rewrites still help auth JSON calls if same-origin `/api` is preferred on Vercel.

---

## 9. Groq API key instructions (for README)

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up (free tier)
3. **API Keys** → Create API key
4. Copy `gsk_...` into Railway variable `GROQ_API_KEY` (never commit)
5. Default model: `llama3-8b-8192`

**Free tier limits (approximate, verify on Groq site):**
- Rate limits per minute/day on chat completions
- Suitable for demo/MVP traffic

---

## 10. Railway deployment guide (summary)

1. Push repo to GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Set **Dockerfile path**: `backend/Dockerfile`
4. Add **Volume** mounted at `/app/data`
5. Set environment variables from `.env.production.example`
6. Deploy → copy public URL (`https://xxx.up.railway.app`)
7. Verify `GET /health` → 200
8. Verify `GET /api/v1/models/status` → `ai_provider: groq`, `models_ready: true`

---

## 11. Vercel deployment guide (summary)

1. Push repo to GitHub
2. [vercel.com](https://vercel.com) → Import repository
3. **Root Directory:** `frontend`
4. Framework: Next.js (auto-detected)
5. Environment variable:
   - `NEXT_PUBLIC_API_URL` = Railway backend URL (no trailing slash)
6. Deploy → copy `https://your-app.vercel.app`
7. Update Railway `CORS_ORIGINS` to Vercel URL → redeploy backend
8. Test: register → upload → chat

---

## 12. Verification checklist

### Local — Ollama mode (regression)

| # | Check |
|---|--------|
| 1 | `AI_PROVIDER=ollama` (default) |
| 2 | `cd backend && pytest -q` → all pass |
| 3 | Upload + chat with local Ollama |

### Local — Groq mode

| # | Check |
|---|--------|
| 4 | `AI_PROVIDER=groq` + valid `GROQ_API_KEY` |
| 5 | `docker compose -f docker-compose.prod.yml up` |
| 6 | `GET /api/v1/models/status` → groq ready |
| 7 | Upload PDF → `chunk_count > 0` |
| 8 | Chat SSE → tokens stream + `done: true` + sources |
| 9 | Docker logs show **no** Ollama connection attempts |

### Production smoke test

| # | Check |
|---|--------|
| 10 | Vercel → Railway CORS OK |
| 11 | Auth login + refresh |
| 12 | Upload + list documents |
| 13 | Chat streaming |
| 14 | Data persists after Railway redeploy (volume) |

---

## 13. Git commands (after implementation)

```bash
# Checkpoint (before coding)
git add -A
git commit -m "chore: checkpoint before Phase 5 deployment"

# After Phase 5 complete
git add -A
git commit -m "feat: Phase 5 production deployment (Groq + Railway + Vercel)"

git push origin main

# Rollback if deployment fails
git revert HEAD --no-edit
git push origin main
```

---

## 14. Troubleshooting (for README section)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Upload 500, no Railway logs | Next.js proxy (dev) | Use `NEXT_PUBLIC_API_URL` direct (already in frontend) |
| `Invalid token` | `SECRET_KEY` mismatch | Same key in Railway + re-login |
| Chat never streams | SSE buffered / wrong URL | Direct `NEXT_PUBLIC_API_URL` for SSE |
| `models_ready: false` (groq) | Missing `GROQ_API_KEY` | Set in Railway |
| Chroma dimension error | Switched embed model | Delete `chroma_db`, re-upload PDFs |
| Railway OOM on start | sentence-transformers load | Increase memory plan or lazy-load |
| CORS error | Wrong `CORS_ORIGINS` | Exact Vercel URL, no trailing slash |
| Empty library after redeploy | No volume | Attach Railway volume at `/app/data` |

---

## 15. Expected free-tier limits (approximate)

| Service | Limit | Notes |
|---------|-------|-------|
| Vercel Hobby | 100GB bandwidth, serverless limits | Next.js 14 OK |
| Railway Free | $5 credit/month, sleep on idle | Volume storage billed |
| Groq Free | RPM/RPD caps | Fine for MVP/demo |

---

## 16. Anticipated file tree (after Phase 5)

```
ai-document-assistant/
├── DEPLOYMENT_PLAN.md              (this file)
├── README.md                       (rewritten)
├── .env.production.example         (new)
├── docker-compose.prod.yml         (new)
├── railway.json                    (new)
├── docker-compose.yml              (comment only)
├── backend/
│   ├── Procfile                    (new)
│   ├── Dockerfile                  (modified — PORT, deps, /app/data)
│   ├── requirements.txt            (modified — groq, sentence-transformers)
│   ├── .env.example                (modified)
│   └── app/
│       ├── config.py               (modified)
│       ├── main.py                 (modified)
│       ├── api/deps.py             (modified)
│       ├── core/
│       │   ├── groq_chat.py        (new)
│       │   ├── groq_availability.py (new)
│       │   ├── sentence_embeddings.py (new)
│       │   ├── provider_factory.py (modified)
│       │   ├── providers.py        (modified)
│       │   ├── rag_pipeline.py     (typing)
│       │   ├── ollama_chat.py      (unchanged logic)
│       │   └── embeddings.py       (unchanged logic)
│       ├── services/               (models, chat, document — typing + status)
│       ├── schemas/models.py       (modified)
│       └── tests/test_groq_provider.py (new, mocked)
├── docs/deployment.md              (new)
└── frontend/
    ├── .env.production             (new — placeholder URL)
    ├── .env.production.example     (new)
    ├── next.config.mjs             (modified)
    ├── lib/api.ts                  (modified — errors)
    ├── lib/types.ts                (modified)
    └── components/dashboard/ModelsStatusBadge.tsx (modified)
```

---

## 17. Approval

Reply **approve** (or note changes, e.g. different embedding model, skip sentence-transformers, use Railway-only docs). After approval, implementation follows **Section 5** order with pytest gate before groq Docker verification.

**Do not write code until this plan is approved.**
