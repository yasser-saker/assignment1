# Docker Setup for AI Takeoff Builder

This project is fully containerized with Docker Compose. It includes:

- **Backend** (`takeoff-backend`): Python 3.12 + FastAPI + Tesseract OCR
- **Frontend** (`takeoff-frontend`): React + Vite served via Nginx
- **Nginx reverse proxy**: Routes `/api/*` to backend, everything else to frontend

---

## Quick Start

### 1. Set API Keys (Optional)

Create a `.env` file or export directly:

```bash
export OPENAI_API_KEY="sk-..."
export KIMI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

### 2. Build & Run

```bash
docker compose up --build -d
```

### 3. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| Frontend (GUI) | http://localhost:8082 | React app with nginx proxy |
| Backend API | http://localhost:8000 | FastAPI (direct access) |
| API via Proxy | http://localhost:8082/api | Same API through nginx |
| Health Check | http://localhost:8082/health | Nginx health |
| API Health | http://localhost:8000/health | Backend health |

> **Note:** The frontend port is `8082` by default. If port `8082` is taken, edit `docker-compose.yml` and change the port mapping (e.g., `"9000:80"`).

---

## HTTPS with Caddy (Production)

To serve the app on a public domain with automatic SSL (e.g., `https://assign.jobotai.site`):

### 1. Update `api/main.py` CORS

Add your domain to the CORS `allow_origins` list:

```python
allow_origins=[
    "http://localhost:5173",
    "...",
    "https://assign.jobotai.site",
],
```

### 2. Add Caddy Block

Edit `/etc/caddy/Caddyfile` on the host server:

```caddy
assign.jobotai.site {
    handle_path /api/* {
        reverse_proxy localhost:8000
    }
    reverse_proxy localhost:8082
}
```

Then reload Caddy:

```bash
caddy reload --config /etc/caddy/Caddyfile
```

### 3. Verify SSL

```bash
curl -s https://assign.jobotai.site/api/health
# Expected: {"status":"ok"}
```

Caddy automatically obtains and renews Let's Encrypt certificates.

---

## Services Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Browser       │─────→│  Nginx          │─────→│  React SPA      │
│                 │      │  (Port 8082)    │      │  (Static files) │
└─────────────────┘      └────────┬────────┘      └─────────────────┘
                                  │
                                  │ /api/*
                                  ▼
                           ┌─────────────────┐
                           │  FastAPI        │
                           │  (Port 8000)    │
                           │                 │
                           │  - OCR Engine   │
                           │  - LLM Client   │
                           │  - Pipeline     │
                           └─────────────────┘
```

---

## Docker Files

| File | Purpose |
|------|---------|
| `Dockerfile.backend` | Python image with Tesseract OCR, PyMuPDF, and all Python deps |
| `Dockerfile.frontend` | Multi-stage Node.js build → Nginx serve |
| `docker-compose.yml` | Orchestrates backend + frontend + networking |
| `nginx.conf` | Reverse proxy rules, SPA fallback, gzip, caching |
| `.dockerignore` | Excludes large files (client_files, outputs, node_modules) from build context |

---

## Volumes

The following host directories are mounted into containers so data persists:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./client_files` | `/app/client_files` | Read-only project PDFs |
| `./outputs` | `/app/outputs` | Generated predictions |
| `./data` | `/app/data` | Intermediate data |
| `./api/dynamic_config.json` | `/app/api/dynamic_config.json` | Settings persistence |
| `./api/jobs_history.json` | `/app/api/jobs_history.json` | Jobs history persistence |

---

## Useful Commands

```bash
# Start everything
docker compose up -d

# View logs
docker compose logs -f

# View backend logs only
docker compose logs -f backend

# Restart a service
docker compose restart backend

# Stop everything
docker compose down

# Rebuild after code changes
docker compose up --build -d

# Run tests inside backend container
docker exec takeoff-backend pytest tests/ -v

# Open a shell in backend
docker exec -it takeoff-backend bash

# Open a shell in frontend
docker exec -it takeoff-frontend sh
```

---

## OCR Inside Docker

Tesseract OCR is pre-installed in the backend image. Verify it works:

```bash
docker exec takeoff-backend tesseract --version
docker exec takeoff-backend python3 -c "from src.ingestion.ocr_engine import OCREngine; print(OCREngine().get_tesseract_info())"
```

---

## Troubleshooting

### Port Already Allocated
If you see `Bind for 0.0.0.0:8082 failed`, change the frontend port in `docker-compose.yml`:
```yaml
ports:
  - "9000:80"   # Use 9000 instead of 8082
```

### Backend Healthcheck Fails
Check logs: `docker compose logs backend`
Common cause: missing `fastapi` or `uvicorn` in `requirements.txt`.

### Frontend Shows Blank Page
Nginx is configured with SPA fallback (`try_files $uri $uri/ /index.html`). If you still see a blank page, check browser console for CORS or 404 errors.

### Large Build Context
The `.dockerignore` excludes `client_files/` from the Docker build context. The folder is mounted as a volume at runtime instead, which is faster and keeps images small.
