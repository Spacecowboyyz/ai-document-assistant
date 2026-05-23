# Production deployment guide

This guide walks you through deploying the AI Document Assistant for free using **Railway** (backend) and **Vercel** (frontend).

---

## What you will deploy

| Piece | Host | Cost |
|-------|------|------|
| Next.js frontend | Vercel | Free tier |
| FastAPI backend | Railway | Free trial credit |
| SQLite + PDFs + Chroma | Railway volume at `/app/data` | Included in Railway usage |
| Chat AI | Groq API | Free tier |
| Embeddings | sentence-transformers in container | No API key |

Local development still uses **Ollama** (`AI_PROVIDER=ollama`). Production uses **Groq** (`AI_PROVIDER=groq`).

---

## Before you start

1. Push this repository to **GitHub**.
2. Create a free account at [console.groq.com](https://console.groq.com) and copy an API key (`gsk_...`).
3. Generate a secret key for JWT:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 1 — Deploy backend on Railway

### 1.1 Create project

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select your repository.
3. Railway detects `railway.json` and builds `backend/Dockerfile`.

### 1.2 Add a volume (required)

Persistent data must survive redeploys:

1. Open your service → **Volumes** → **Add Volume**.
2. Mount path: **`/app/data`**

This stores SQLite, uploaded PDFs, and Chroma embeddings.

### 1.3 Set environment variables

In **Variables**, add (from `.env.production.example`):

| Variable | Example value |
|----------|----------------|
| `AI_PROVIDER` | `groq` |
| `GROQ_API_KEY` | `gsk_your_key` |
| `GROQ_CHAT_MODEL` | `llama3-8b-8192` |
| `SECRET_KEY` | (64-char hex from python secrets) |
| `DATABASE_URL` | `sqlite:////app/data/app.db` |
| `CHROMA_DB_PATH` | `/app/data/chroma_db` |
| `UPLOADS_DIR` | `/app/data/uploads` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` (update after Vercel) |
| `ENVIRONMENT` | `production` |

Railway sets `PORT` automatically — do not override it.

### 1.4 Deploy and verify

1. Click **Deploy** and wait for the build to finish.
2. Open **Settings** → **Networking** → **Generate Domain**.
3. Test health: `https://YOUR-RAILWAY-URL/health` → should return JSON with `"status":"ok"`.
4. Test models: `https://YOUR-RAILWAY-URL/api/v1/models/status` → `"ai_provider":"groq"`, `"models_ready":true`.

Copy your Railway URL — you need it for Vercel.

---

## Step 2 — Deploy frontend on Vercel

### 2.1 Import project

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**.
2. Import the same GitHub repository.
3. Set **Root Directory** to `frontend`.
4. Framework preset: **Next.js** (auto-detected).

### 2.2 Environment variable

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RAILWAY-URL` (no trailing slash) |

### 2.3 Deploy

Click **Deploy**. When finished, copy your Vercel URL (e.g. `https://your-app.vercel.app`).

### 2.4 Update CORS on Railway

1. Return to Railway → **Variables**.
2. Set `CORS_ORIGINS` to your exact Vercel URL (no trailing slash).
3. Redeploy the backend.

---

## Step 3 — Smoke test

1. Open your Vercel URL in a browser.
2. **Register** a new account.
3. **Upload** a PDF — wait for indexing.
4. Open the document and **chat** — you should see streaming tokens and sources.

---

## Local Groq test (before cloud deploy)

```bash
# In backend/.env
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_key

# From repo root
docker compose -f docker-compose.prod.yml up --build
```

Frontend (separate terminal):

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

---

## ChromaDB and provider switching

Embeddings are stored under **`{CHROMA_DB_PATH}/{AI_PROVIDER}/`** (e.g. `chroma_db/ollama` vs `chroma_db/groq`). This prevents mixing **768-dim** (Ollama) and **384-dim** (MiniLM) vectors.

If you change `AI_PROVIDER` on the same volume, old documents for the other provider remain in a separate subfolder — re-upload PDFs for the new provider if needed.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| CORS error in browser | Wrong `CORS_ORIGINS` | Set exact Vercel URL, redeploy Railway |
| `models_ready: false` | Missing Groq key | Set `GROQ_API_KEY` in Railway |
| Chat 429 error | Groq rate limit | Wait 30–60 seconds, retry |
| Upload works locally but not on Vercel | Wrong API URL | Check `NEXT_PUBLIC_API_URL` on Vercel |
| Documents gone after redeploy | No volume | Mount Railway volume at `/app/data` |
| Railway build OOM | Large ML deps | Upgrade Railway plan or wait for cold start |
| Session expired | Token TTL | Log in again (15 min access token) |

---

## Free tier limits (approximate)

| Service | Notes |
|---------|--------|
| **Groq** | Rate limits per minute/day on free tier |
| **Vercel Hobby** | Bandwidth and build limits |
| **Railway** | Monthly credit; idle sleep possible on free trial |

Check each provider’s dashboard for current limits.

---

## Rollback

If deployment fails after a git push:

```bash
git revert HEAD --no-edit
git push origin main
```

Redeploy Railway and Vercel from the previous commit.
