# AI Document Assistant

Upload PDFs, ask questions, and get **streaming answers with page citations** — powered by RAG (retrieval-augmented generation).

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind |
| Backend | FastAPI, SQLAlchemy, Alembic, JWT auth |
| Vector DB | ChromaDB |
| Local AI | Ollama (`llama3` + `nomic-embed-text`) |
| Production AI | Groq (`llama3-8b-8192`) + sentence-transformers (`all-MiniLM-L6-v2`) |
| Database | SQLite |

## Architecture

```
Browser (Vercel)
    → FastAPI (Railway)
        → Groq API (chat)
        → sentence-transformers (embeddings, in-container)
        → ChromaDB + SQLite + PDFs on /app/data volume
```

Local development uses **Ollama** on your machine instead of Groq.

---

## Local development

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) running locally

### 1. Pull Ollama models

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
ollama serve
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# Edit SECRET_KEY if needed; AI_PROVIDER=ollama (default)

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install
npm run dev
```

Open http://localhost:3000

### 4. Docker (optional, with host Ollama)

```bash
docker compose up --build
```

Uses `host.docker.internal` for Ollama. See `docker-compose.yml`.

---

## Production deployment

Full beginner-friendly steps: **[docs/deployment.md](docs/deployment.md)**

Quick summary:

1. **Groq API key** — [console.groq.com](https://console.groq.com) → API Keys → Create (free).
2. **Railway** — deploy `backend/Dockerfile`, volume at `/app/data`, env from `.env.production.example`.
3. **Vercel** — root `frontend/`, set `NEXT_PUBLIC_API_URL` to Railway URL.
4. Update Railway `CORS_ORIGINS` to your Vercel URL.

---

## Environment variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `ollama` | `ollama` or `groq` |
| `GROQ_API_KEY` | — | Required when `AI_PROVIDER=groq` |
| `GROQ_CHAT_MODEL` | `llama3-8b-8192` | Groq chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama |
| `OLLAMA_CHAT_MODEL` | `llama3` | Ollama chat model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embeddings |
| `CHROMA_DB_PATH` | `./chroma_db` | Base path; actual store is `{path}/{AI_PROVIDER}/` |
| `UPLOADS_DIR` | `./uploads` | PDF storage |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLite connection |
| `SECRET_KEY` | (dev default) | JWT signing — change in production |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

See `backend/.env.example` and `.env.production.example`.

### Frontend

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL for upload + SSE (required in production) |

---

## Verification checklist

### Ollama mode (default)

```bash
cd backend && pytest -q
```

- [ ] Register / login
- [ ] Upload PDF → `chunk_count > 0`
- [ ] Chat streams tokens + sources

### Groq mode

```bash
# backend/.env: AI_PROVIDER=groq, GROQ_API_KEY=gsk_...
docker compose -f docker-compose.prod.yml up --build
```

- [ ] `GET /api/v1/models/status` → `ai_provider: groq`, `models_ready: true`
- [ ] Upload + chat without Ollama running
- [ ] No Ollama requests in backend logs

---

## Screenshots

_Add screenshots of the dashboard, upload flow, and chat with sources here after deployment._

---

## Project structure

```
backend/          FastAPI app, RAG pipeline, providers
frontend/         Next.js UI
docs/             deployment.md, architecture.md
docker-compose.yml       Local Ollama dev
docker-compose.prod.yml  Groq production test
railway.json      Railway build config
```

---

## Git commands

```bash
# After Phase 5 changes
git add -A
git commit -m "feat: Phase 5 production deployment (Groq + Railway + Vercel)"
git push origin main

# Rollback if deployment fails
git revert HEAD --no-edit
git push origin main
```

---

## License

MIT (or your chosen license)
