#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose -f docker-compose.yml -f docker-compose.ui.yml up -d "$@"

echo "Demo UI: http://localhost:8080"
echo "API: http://localhost:8000"
echo "Health: http://localhost:8000/health"
echo "Docs: http://localhost:8000/docs"
echo ""
echo "Logs: docker compose logs -f"
echo "Stop: docker compose down"
