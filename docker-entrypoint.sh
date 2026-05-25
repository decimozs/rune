#!/bin/sh
set -e

chown -R appuser:appuser /app/data /app/outputs 2>/dev/null || true

exec su -s /bin/sh appuser -c "exec $*"
