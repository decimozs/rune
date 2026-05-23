# Quick Start

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- `make` (optional — for Makefile automation)

## Run Locally

```bash
# Install dependencies
uv sync

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

Open [`index.html`](../index.html) in a browser (no server needed — opens as `file://`). Drag-and-drop files, choose mode (sync/background/batch), toggle Raw/Preview tabs. CORS enabled for file:// access.

## Run with Docker Compose

```bash
# Start both services (API + Gotenberg)
docker compose up -d

# Stop
docker compose down
```

API at `http://localhost:8000`, Gotenberg at `http://localhost:3000`. Both services include Docker healthchecks — `ocr-api` waits for `gotenberg: service_healthy` before starting.

OCR assets (extracted markdown images) served at `http://localhost:8000/assets/`.
