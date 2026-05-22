# Quick Start

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

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

## Run with Docker Compose

```bash
# Start both services (API + Gotenberg)
docker compose up -d

# Stop
docker compose down
```

API at `http://localhost:8000`, Gotenberg at `http://localhost:3000`.
