# Project Structure

```
exist-ocr/
│
├── app/
│   ├── main.py                 # FastAPI entry point — starts all services
│   ├── config.py               # Configuration from .env or environment variables
│   │
│   ├── routes/
│   │   ├── ocr.py              # All OCR API endpoints
│   │   └── health.py           # Health check endpoints
│   │
│   ├── services/
│   │   ├── ocr.py              # Main OCR logic — connects all pieces together
│   │   ├── engine.py           # PaddleOCR and PPStructureV3 model loading
│   │   ├── formatter.py        # Converts raw OCR output to structured JSON
│   │   ├── xml_formatter.py    # Converts OCR output to XML format
│   │   ├── markdown.py         # Converts OCR output to Markdown format
│   │   ├── converter.py        # Document conversion via Gotenberg
│   │   ├── processor.py        # File processing pipeline
│   │   ├── async_job.py        # Background and batch job processing
│   │   ├── auth.py             # API key verification
│   │   ├── db.py               # SQLite database for key storage
│   │   ├── url_guard.py        # URL safety checks (prevents SSRF)
│   │   ├── log_ctx.py          # Logging context, JSON formatter, request-ID
│   │   ├── cleanup.py          # Automatic cleanup of old output files
│   │   └── exceptions.py       # Custom error types
│   │
│   ├── schemas/
│   │   ├── ocr.py              # Data models for OCR results
│   │   └── response.py         # API response structure
│   │
│   └── datasets/               # Sample files for testing
│
├── nginx/
│   ├── default.conf            # nginx config with demo UI at root + /assets/
│   └── default.no-ui.conf      # nginx config for headless (assets only)
│
├── Dockerfile                  # Builds the OCR API container
├── docker-compose.yml          # Defines all services (API, nginx, Gotenberg)
├── docker-compose.no-ui.yml    # Override: removes demo UI (assets only)
├── docker-entrypoint.sh        # Fixes file permissions at container startup
│
├── Makefile                    # Common commands (up, down, test, dev)
├── index.html                  # Demo frontend (drag-and-drop UI)
├── .env.example                # Configuration template
├── pyproject.toml              # Python project metadata and dependencies
│
├── scripts/                    # Testing and management scripts
│
├── tests/                      # Unit tests
│
└── kb/                         # Documentation (this folder)
    ├── research.md             # Academic references and studies
    ├── tech/                   # Technical documentation
    └── user-guide/             # End-user documentation
```
