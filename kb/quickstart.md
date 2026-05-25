# Quick Start

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- `make` (optional — for Makefile automation)
- System dependencies — see [Prerequisites doc](prerequisites.md) for per-OS install guide

## Run Locally

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y \
  libmagic1 libgl1 libglib2.0-0 libsm6 libxext6 \
  libxrender1 libgomp1 libstdc++6 libc6 curl poppler-utils

# Install Python dependencies
uv sync

# Start Gotenberg (for office doc + URL/HTML conversion)
docker run -d --rm -p 3000:3000 --name gotenberg gotenberg/gotenberg:8

# Production
uv run fastapi run app/main.py --port 8000

# Development (hot reload)
uv run fastapi dev app/main.py --port 8000
```

Server at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Makefile

Common tasks automated via `make`:

```bash
make dev          # hot-reload dev server
make run          # production server
make up           # docker compose up -d
make down         # docker compose down
make logs         # tail all container logs
make rebuild      # full clean rebuild (down + build --no-cache + up)
make test-routes  # validate all API routes
make test-formats # test all file formats
make benchmark    # run OCR benchmark
make health       # check liveness + readiness
```

Run `make help` to list all targets.

## Demo UI

Open [`index.html`](../index.html) in a browser (no server needed — opens as `file://`). Three source types: **File** (drag-and-drop), **URL** (text input), **HTML** (upload + assets). Choose mode (sync/background/batch), toggle Raw/Preview/Visualize tabs. Visualize tab renders confidence-colored bboxes overlaid on the original image via canvas. CORS enabled for file:// access.

## Run with Docker Compose

```bash
# Start both services (API + Gotenberg)
docker compose up -d

# Stop
docker compose down
```

API at `http://localhost:8000`, Gotenberg at `http://localhost:3000`. Both services include Docker healthchecks — `ocr-api` waits for `gotenberg: service_healthy` before starting.

Note: Docker Compose overrides `OCR_GOTENBERG_URL` to `http://gotenberg:3000` (internal Docker DNS). When running the OCR API locally (not in Docker), the `.env` default `http://localhost:3000` is used instead.

OCR assets (extracted markdown images) served at `http://localhost:8000/assets/`.
