# AI Document Assistant — Setup Guide

## Local Model Setup (Ollama)

1. Install Ollama: https://ollama.com/download
2. Pull required models:

   ```bash
   ollama pull llama3
   ollama pull nomic-embed-text
   ```

3. Start Ollama server:

   ```bash
   ollama serve
   ```

4. Verify at: http://localhost:11434

For Docker, point the API at the host Ollama instance:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## Authentication (Phase 3)

1. Copy `backend/.env.example` to `backend/.env`
2. Generate a secret key:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Set in `.env`:

   ```env
   SECRET_KEY=<your-64-char-hex-string>
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   REFRESH_TOKEN_EXPIRE_DAYS=7
   DATABASE_URL=sqlite:///./data/app.db
   ```

4. Register and login via Swagger at `http://localhost:8000/docs` under **auth** endpoints.

## Docker Run (SQLite persistence)

The SQLite database is stored in `backend/data/`. Mount it as a volume so users and documents persist across restarts.

### PowerShell (Windows)

```powershell
cd backend
docker build -t ai-doc-assistant-backend .
docker run -p 8000:8000 `
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 `
  -v "${PWD}/data:/app/data" `
  --env-file .env `
  ai-doc-assistant-backend
```

### Bash (Mac / Linux)

```bash
cd backend
docker build -t ai-doc-assistant-backend .
docker run -p 8000:8000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v "$(pwd)/data:/app/data" \
  --env-file .env \
  ai-doc-assistant-backend
```

## Running Tests

From `backend/`:

```bash
pytest -q
```

All tests run offline with mocked Ollama and isolated per-test SQLite files.
