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
