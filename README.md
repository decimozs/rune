# Exist OCR Service

Internal OCR service for **Exist Software Labs**. Uses [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (PP-OCRv4) to extract text and bounding boxes from uploaded images, PDFs, and office documents.

> **Status: Heavy Development & Testing** — API, architecture, and features are subject to change.

## Tech Stack

- **Python** 3.11+ / **FastAPI** / **uv**
- **PaddleOCR** (PP-OCRv4) — OCR + structure recognition
- **pydantic-settings** — env config
- **aiofiles** — async file I/O
- **python-magic** — MIME type validation
- **Gotenberg** — document-to-PDF conversion (reused httpx client)
- **Docker** — multi-stage containerized deployment
- **CORS** — `allow_origins=["*"]` for internal demo access
- **Static Files** — `/assets` serves markdown images from OCR output

## Architecture

```mermaid
flowchart TB
  Client(["Client / curl / Scripts"])

  subgraph FastAPI["FastAPI Application"]
    MW["Middleware\ntiming · X-Processing-Time-Ms"]
    Routes["routes/\nocr.py + health.py\nPOST /ocr/parse\nPOST /ocr/parse/batch\nGET /ocr/parse/batch/{id}\nPOST /ocr/parse/jobs\nGET /ocr/parse/jobs/{id}\nGET /health\nGET /health/ready"]
    PROC["processor.py\nshared pipeline\nwrite → magic → convert → OCR → cleanup"]
    BP["BatchProcessor\nin-memory queue\n1hr TTL"]
    BJP["BackgroundProcessor\nsingle-job queue\n1hr TTL"]
    OCRS["OCRService\norchestrator"]
    Conv["DocumentConverter\nreused httpx client"]
  end

  subgraph Paddle["PaddleOCR"]
    ENGINE["OCREngine\nPP-OCRv4"]
    STRUCT["StructureEngine\nPPStructureV3"]
  end

  Gotenberg[("Gotenberg\n(docker)")]
  FS[("File System\n/uploads")]

  Client -->|multipart/file| MW
  MW --> Routes

  Routes -->|sync| PROC
  Routes -->|async batch| BP
  Routes -->|async single| BJP

  BP -->|background| PROC
  BJP -->|background| PROC

  PROC -->|to_thread| ENGINE
  PROC -->|to_thread| STRUCT
  PROC -->|needs conversion| Conv
  Conv -->|HTTP POST| Gotenberg
  Gotenberg -->|PDF| Conv

  ENGINE -->|OCR result| PROC
  STRUCT -->|markdown| PROC

  PROC -->|read| FS

  style Client fill:#333,stroke:#000,stroke-width:1px,color:#fff
  style FastAPI fill:#fafafa,stroke:#999,stroke-width:1px,color:#666,stroke-dasharray:6 4
  style Paddle fill:#fafafa,stroke:#999,stroke-width:1px,color:#666,stroke-dasharray:6 4
  style Routes fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style MW fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style PROC fill:#ddd,stroke:#000,stroke-width:1.5px,color:#000
  style BP fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style BJP fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style OCRS fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style Conv fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style ENGINE fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style STRUCT fill:#eee,stroke:#555,stroke-width:1px,color:#000
  style Gotenberg fill:#fff,stroke:#000,stroke-width:2px,color:#000
  style FS fill:#fff,stroke:#000,stroke-width:2px,color:#000
```

## Documentation

| Topic | Description |
|---|---|---|
| [Quick Start](docs/quickstart.md) | Prerequisites, local run, docker-compose, make |
| [Configuration](docs/configuration.md) | Environment variables table |
| [API Reference](docs/api.md) | All endpoints with curl examples and responses (JSON, Markdown, XML) |
| [Testing Scripts](docs/scripts.md) | Scripts table and usage examples |
| [Project Structure](docs/structure.md) | Directory layout |
| [Demo Frontend](index.html) | Standalone UI — drag-and-drop, 3 modes, markdown/XML preview |
| [Makefile](Makefile) | Common task automation (dev, Docker, scripts) |
