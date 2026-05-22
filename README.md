# Exist OCR Service

Internal OCR service for **Exist Software Labs**. Uses [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (PP-OCRv4) to extract text and bounding boxes from uploaded images, PDFs, and office documents.

> **Status: Heavy Development & Testing** — API, architecture, and features are subject to change.

## Tech Stack

- **Python** 3.11+ / **FastAPI** / **uv**
- **PaddleOCR** (PP-OCRv4) — OCR + structure recognition
- **pydantic-settings** — env config
- **aiofiles** — async file I/O
- **python-magic** — MIME type validation
- **Gotenberg** — document-to-PDF conversion
- **Docker** — containerized deployment

## Architecture

```mermaid
flowchart TB
  Client[Client / curl / Scripts]

  subgraph FastAPI["FastAPI Application"]
    Routes["routes/ocr.py\nPOST /ocr/parse\nPOST /ocr/parse/batch\nGET /ocr/parse/batch/{id}\nPOST /ocr/parse/jobs\nGET /ocr/parse/jobs/{id}"]
    BP["BatchProcessor\nin-memory queue\n1hr TTL"]
    BJP["BackgroundProcessor\nsingle-job queue\n1hr TTL"]
    OCRS["OCRService\norchestrator"]
    Conv["DocumentConverter\nGotenberg client"]
  end

  subgraph Paddle["PaddleOCR"]
    ENGINE["OCREngine\nPP-OCRv4"]
    STRUCT["StructureEngine\nPPStructureV3"]
  end

  Gotenberg[("Gotenberg\n(docker)")]
  FS[("File System\n/uploads")]

  Client -->|multipart/file| Routes

  Routes -->|sync| OCRS
  Routes -->|async batch| BP
  Routes -->|async single| BJP

  BP -->|background| OCRS
  BJP -->|background| OCRS

  OCRS -->|to_thread| ENGINE
  OCRS -->|to_thread| STRUCT
  OCRS -->|needs conversion| Conv
  Conv -->|HTTP POST| Gotenberg
  Gotenberg -->|PDF| Conv

  ENGINE -->|OCR result| OCRS
  STRUCT -->|markdown| OCRS

  Routes -->|write| FS
  OCRS -->|read| FS

  style Client fill:#e1f5fe
  style FastAPI fill:#f3e5f5
  style Paddle fill:#e8f5e9
  style Gotenberg fill:#fff3e0
  style FS fill:#fce4ec
```

## Documentation

| Topic | Description |
|---|---|
| [Quick Start](docs/quickstart.md) | Prerequisites, local run, docker-compose |
| [Configuration](docs/configuration.md) | Environment variables table |
| [API Reference](docs/api.md) | All endpoints with curl examples and responses |
| [Testing Scripts](docs/scripts.md) | Scripts table and usage examples |
| [Project Structure](docs/structure.md) | Directory layout |
