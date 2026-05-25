"""Logging context helpers for structured, traceable logs.

Provides:
    - request_id contextvar (set by middleware, read by formatter)
    - identity contextvar (set by auth dependency)
    - LogContextFilter to inject context into log records
    - JSONFormatter for structured log output
    - sanitize_url for safe URL logging (no query/fragment leak)
"""

import contextvars
import json
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
identity_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "identity", default=""
)


def sanitize_url(url: str) -> str:
    """Strip query/fragment/auth from URL for safe logging."""
    parsed = urlparse(url)
    hostname = parsed.hostname or "?"
    path = parsed.path or "/"
    return f"{parsed.scheme}://{hostname}{path}"


class LogContextFilter(logging.Filter):
    """Injects request_id and identity into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.identity = identity_var.get()
        return True


class JSONFormatter(logging.Formatter):
    """Output logs as JSON lines. Compatible with log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
            "identity": getattr(record, "identity", ""),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)
