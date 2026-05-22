# Exist OCR Service

Internal OCR service for **Exist Software Labs**. Uses [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (PP-OCRv4) to extract text and bounding boxes from uploaded images and PDFs.

> **Status: Heavy Development & Testing** — API, architecture, and features are subject to change.

## Tech Stack

- **Python** 3.11+
- **FastAPI** — web framework
- **PaddleOCR** — OCR engine (PP-OCRv4)
- **pydantic-settings** — environment config
- **aiofiles** — async file I/O
- **python-magic** — MIME type validation
- **uv** — package & project management
- **Docker** — containerized deployment

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

### Run Locally

```bash
# Install dependencies
uv sync

# Production
uv run fastapi run app/main.py --port 8000

# Development (hot reload)
uv run fastapi dev app/main.py --port 8000
```

Server at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Run with Docker

```bash
docker build -t exist-ocr .
docker run -p 8000:80 exist-ocr
```

## Configuration

Settings loaded from `.env` file (see `.env.example`) or environment variables with `OCR_` prefix:

| Variable | Default | Description |
|---|---|---|
| `OCR_LANG` | `en` | OCR language code |
| `OCR_VERSION` | `PP-OCRv4` | PaddleOCR model version |
| `OCR_ENABLE_MKLDNN` | `false` | Intel MKL-DNN CPU acceleration |
| `OCR_USE_TEXTLINE_ORIENTATION` | `true` | Detect textline orientation |
| `OCR_MAX_FILE_SIZE` | `52428800` | Max upload size (bytes, ~50MB) |
| `OCR_UPLOAD_DIR` | `/tmp` | Temp directory for uploads |
| `OCR_ALLOWED_CONTENT_TYPES` | `image/jpeg,image/png,...` | Allowed MIME types |
| `OCR_OUTPUT_DIR` | `app/outputs` | Markdown output directory |
| `OCR_LOG_LEVEL` | `INFO` | Log level |

## API

### `POST /ocr/parse`

Upload an image or PDF for OCR extraction.

**Query Parameters:**
- `format` — `json` (default) or `markdown`

**Request:** `multipart/form-data` with field `file`

**Allowed MIME types:** `image/jpeg`, `image/png`, `image/bmp`, `image/tiff`, `image/webp`, `application/pdf`

**Validation:** Content-Type header checked against allowed list, then actual file bytes verified via `python-magic` (MIME sniffing).

**cURL (JSON):**

```bash
curl -X POST http://localhost:8000/ocr/parse \
  -F "file=@path/to/image.png"
```

**cURL (Markdown):**

```bash
curl -X POST "http://localhost:8000/ocr/parse?format=markdown" \
  -F "file=@path/to/image.png"
```

**Success Response (200):**

```json
{
  "success": true,
  "metadata": {
    "timestamp": "2026-05-21T12:00:00Z",
    "model": "PP-OCRv4",
    "format": "json",
    "processing_time_ms": 123.45,
    "file_name": "image.png",
    "file_type": "image/png"
  },
  "data": {
    "pages": [
      {
        "page": 1,
        "words": [
          {
            "text": "Hello World",
            "confidence": 0.9876,
            "bbox": {
              "points": [[10, 20], [100, 20], [100, 40], [10, 40]]
            }
          }
        ],
        "extracted_text": "Hello World"
      }
    ]
  }
}
```

**Error Responses:**

| Status | Code | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing filename |
| 413 | `FILE_TOO_LARGE` | Exceeds `OCR_MAX_FILE_SIZE` |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | MIME type not in allowed list |
| 415 | `CONTENT_MISMATCH` | Declared MIME type does not match actual file bytes |
| 500 | `OCR_ERROR` | Engine processing failure |
| 500 | `INTERNAL_ERROR` | Unhandled exception |

```json
{
  "success": false,
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "Unsupported file type: image/gif. Allowed: image/jpeg, image/png, ..."
  }
}
```

## Testing Scripts

Convenience scripts in `scripts/` for automated testing:

| Script | Purpose |
|---|---|
| `test_ocr.sh` | Run OCR on all files in `app/datasets/`, save JSON and Markdown responses to timestamped output dir |
| `benchmark.sh [runs=3] [url]` | Run OCR N times per file, print min/max/avg/median timing stats |
| `stress.sh [concurrency=5] [url]` | Fire N parallel requests per file, report success rate and RPS |
| `compare_runs.sh [url]` | Run OCR twice, diff outputs (ignoring timestamps), exit 0 if identical |
| `run_test.sh [url]` | Execute full pipeline: parse, benchmark, compare, stress |
| `cleanup.sh [--older-than N \| --all \| --dry-run]` | List and delete old test output directories with confirmation |

**Examples:**

```bash
./scripts/test_ocr.sh
./scripts/benchmark.sh 5
./scripts/stress.sh 10
./scripts/compare_runs.sh
./scripts/run_test.sh
./scripts/cleanup.sh --older-than 7
```

All scripts check that the server is running before proceeding.

## Project Structure

```
app/
├── main.py               # FastAPI app entrypoint, lifespan, exception handlers
├── config.py             # pydantic-settings config (OCR_ env vars)
├── routes/
│   └── ocr.py            # OCR endpoint: upload, validate, process, respond
├── services/
│   ├── ocr.py            # Orchestrator (composes engine, formatter, markdown)
│   ├── engine.py         # PaddleOCR + PPStructureV3 model init & prediction
│   ├── formatter.py      # Raw OCR output → structured JSON
│   ├── markdown.py       # PPStructureV3 markdown conversion + image saving
│   └── exceptions.py     # Custom exceptions (OCRValidationError, OCRRuntimeError)
├── schemas/
│   ├── ocr.py            # Domain models: BoundingBox, WordBlock, OCRPage, OCRResponse
│   └── response.py       # API envelope: APIResponse, ResponseMetadata, ErrorDetail
└── datasets/             # Sample files for testing
    ├── sample_image.png
    └── sample_pdf.pdf

scripts/                  # Automation & testing scripts
├── test_ocr.sh
├── benchmark.sh
├── stress.sh
├── compare_runs.sh
├── run_test.sh
└── cleanup.sh

tests/
└── outputs/              # Test script output directories (auto-created, gitignored)
