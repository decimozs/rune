# Quick Start

Two ways to run: **Docker Compose** (recommended — everything packaged) or **local** (for development).

## Option 1: Docker Compose (Recommended)

This starts all services — the OCR application, Gotenberg (document converter), and nginx (image server).

```bash
# Start all services in the background
docker compose up -d

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
  -H "X-API-Key: sk-local-dev" \
  -F "file=@document.png"

# Get text as markdown instead
curl -X POST "http://localhost:8000/ocr/parse?format=markdown" \
  -H "X-API-Key: sk-local-dev" \
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

The server runs at `http://localhost:8000`. Images are served directly by FastAPI (no nginx in local dev mode).

## Makefile Automation

| Command | What It Does |
|---|---|
| `make up` | Start all Docker services |
| `make down` | Stop all Docker services |
| `make logs` | See logs from all containers |
| `make rebuild` | Full clean rebuild (down, build, up) |
| `make dev` | Start development server with hot reload |
| `make test` | Run unit tests |
| `make health` | Check if the API is running and ready |

Run `make help` to see all available commands.

## Demo UI

Open `index.html` in your browser (double-click the file — no server needed). This provides a simple drag-and-drop interface to upload files, choose output format, and see results with confidence-colored bounding boxes overlaid on the page image.
