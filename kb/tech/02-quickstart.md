# Quick Start

Two ways to run: **Docker Compose** (recommended — everything packaged) or **local** (for development).

## Option 1: Docker Compose (Recommended)

This starts all services — the OCR application, Gotenberg (document converter), and nginx (image server + demo UI).

### From a Release ZIP

```bash
unzip exist-ocr-v*.zip
cd exist-ocr
cp .env.example .env
docker compose up -d
```

The demo UI is served at `http://localhost:8080`. The API is at `http://localhost:8000`.

### From Git

```bash
git clone <repo-url>
cd exist-ocr
cp .env.example .env
docker compose up -d
```

### Managing Services

```bash
# Check they are running and healthy
docker compose ps

# See logs from all services
docker compose logs -f

# Stop everything (keeps data in volumes for next start)
docker compose down
```

Once started:

| Service | URL | What It Does |
|---|---|---|
| OCR API | `http://localhost:8000` | Process files, extract text |
| nginx (images) | `http://localhost:8080` | Serve page images from OCR output |
| Gotenberg | `http://localhost:3000` | Convert office docs to PDF |
| API docs | `http://localhost:8000/docs` | Interactive Swagger UI to test endpoints |

### Quick Test

```bash
# Upload an image and get text back as JSON
curl -X POST http://localhost:8000/ocr/parse \
  -F "file=@document.png"

# Get text as markdown instead
curl -X POST "http://localhost:8000/ocr/parse?format=markdown" \
  -F "file=@document.png"
```

The response includes a `page_image_url` field pointing to nginx (e.g., `http://localhost:8080/assets/pages/...`). Open that URL in your browser to see the processed page image.

## Option 2: Local Development

For development without Docker — useful when you are modifying code and want hot reload.

```bash
# 1. Install system dependencies (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y \
  libmagic1 libgl1 libglib2.0-0 libsm6 libxext6 \
  libxrender1 libgomp1 libstdc++6 libc6 curl poppler-utils

# 2. Install Python dependencies
uv sync

# 3. Start Gotenberg (for office documents and URL/HTML conversion)
docker run -d --rm -p 3000:3000 --name gotenberg gotenberg/gotenberg:8

# 4. Start the dev server with hot reload
uv run fastapi dev app/main.py --port 8000
```

The server runs at `http://localhost:8000`. Page image URLs omit the host (e.g., `/assets/pages/...`) — open them by prepending `http://localhost:8000` or serve the `app/outputs` directory via your own static server. There is no nginx in local dev mode, and FastAPI does not mount a static file handler.

## Makefile Automation

| Command | What It Does |
|---|---|
| `make up` | Start all Docker services with demo UI at `http://localhost:8080` |
| `make up-ui` | Same as `make up` (alias) |
| `make down` | Stop all Docker services |
| `make logs` | See logs from all containers |
| `make rebuild` | Full clean rebuild (down -v, build --no-cache, up) |
| `make dev` | Start Gotenberg container + dev server with hot reload; stops Gotenberg on exit |
| `make test` | Run unit tests |
| `make health` | Check if the API is running and ready |

Run `make help` to see all available commands.

## Demo UI

The demo UI is served at `http://localhost:8080` by default (`make up` or `docker compose up -d`). Drag and drop files, choose output format, and see results.

To run headless (API only, no UI):
```bash
docker compose -f docker-compose.yml -f docker-compose.no-ui.yml up -d
```

You can also open `index.html` standalone by double-clicking the file — no server needed. The UI fetches from the API URL you enter.
