# API Reference

All OCR endpoints start with `/ocr`. Health checks are at the root level (`/health`).

## File Types You Can Process

Three source types are supported:

| Source | What It Is | Needs Gotenberg? |
|---|---|---|
| **File** | Images (PNG, JPG, BMP, TIFF, WebP), PDFs, Word docs, Excel spreadsheets, PowerPoint presentations | Only for office documents |
| **URL** | A web page address — the system fetches the page, converts it to PDF, then reads the text | Yes |
| **HTML** | Upload an HTML file with optional CSS/images — rendered to PDF, then text extracted | Yes |

## Health Endpoints

### `GET /health`

Simple check: is the application running? Returns 200 if alive. Used by Docker to verify the container started correctly.

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

### `GET /health/ready`

Full readiness check: are all dependencies loaded (OCR engine, document structure engine)? This can take 20-40 seconds on first startup while models download. Returns 503 if not ready.

```bash
curl http://localhost:8000/health/ready
# → {"status": "ok", "checks": {"ocr_engine": "ok", "structure_engine": "ok"}}
```

## Authentication

Most endpoints require an API key sent as the `X-API-Key` header. Health endpoints are always open.

Three authentication modes:

| Mode | How It Works | When To Use |
|---|---|---|
| **Disabled** | Default — no header required | Local development only |
| **Environment variable** | Keys listed in `.env` file | Simple setups, restart needed to change keys |
| **SQLite database** | Keys stored as hashes in a database file | Production — keys work immediately, no restart needed |

The recommended setup for production is database-backed auth:

```bash
# Generate a key
uv run python scripts/create_api_key.py --name alice --team engineering --db-path app/data/ocr.db
# Output: API key: sk_live_AbCdEfGhIjKlMnOp

# Use it
curl -X POST http://localhost:8000/ocr/parse \
  -H "X-API-Key: sk_live_AbCdEfGhIjKlMnOp" \
  -F "file=@document.pdf"
```

## OCR Endpoints

### Sync — `POST /ocr/parse`

Upload one file, get results back when processing finishes. The simplest endpoint — use this when you want a single response.

**Query parameters** (all optional):

| Parameter | Values | Default | What It Does |
|---|---|---|---|
| `format` | `json`, `markdown`, `xml` | `json` | Output format |
| `include_bbox` | `true`, `false` | `true` | Include position coordinates (JSON only) |
| `include_confidence` | `true`, `false` | `true` | Include accuracy score per word (JSON only) |
| `include_extracted_text` | `true`, `false` | `true` | Include full plain text (JSON only) |
| `include_page_image` | `true`, `false` | `true` | Include image URL per page (JSON only) |

```bash
# Basic: upload an image, get JSON
curl -X POST http://localhost:8000/ocr/parse \
  -H "X-API-Key: sk-local-dev" \
  -F "file=@receipt.png"

# Lightweight: just the text, no positions or images
curl -X POST "http://localhost:8000/ocr/parse?include_bbox=false&include_confidence=false&include_page_image=false" \
  -H "X-API-Key: sk-local-dev" \
  -F "file=@receipt.png"

# Markdown: for documents with tables and structure
curl -X POST "http://localhost:8000/ocr/parse?format=markdown" \
  -H "X-API-Key: sk-local-dev" \
  -F "file=@report.docx"

# XML output
curl -X POST "http://localhost:8000/ocr/parse?format=xml" \
  -H "X-API-Key: sk-local-dev" \
  -F "file=@invoice.pdf"
```

**Response** (JSON format):

```json
{
  "success": true,
  "metadata": {
    "timestamp": "2026-05-21T12:00:00Z",
    "model": "PP-OCRv4",
    "format": "json",
    "processing_time_ms": 123.45,
    "file_name": "receipt.png",
    "file_type": "image/png"
  },
  "data": {
    "pages": [
      {
        "page": 1,
        "words": [
          {
            "text": "Total: $42.00",
            "confidence": 0.9876,
            "bbox": {
              "points": [[10, 20], [180, 20], [180, 40], [10, 40]]
            }
          }
        ],
        "extracted_text": "Total: $42.00",
        "page_image_url": "http://localhost:8080/assets/pages/a1b2c3d4e5f6/page_1.png",
        "ocr_width": 1200,
        "ocr_height": 1600
      }
    ]
  }
}
```

The `page_image_url` points to nginx (port 8080), not the main API. Open that URL to see the image with detected text regions.

**Error responses:**

| Status | Meaning |
|---|---|
| 400 | Bad request — missing filename, invalid URL |
| 404 | Job or batch ID not found |
| 413 | File too large (default limit: 50MB) |
| 415 | File type not supported |
| 502 | Document conversion failed (Gotenberg issue) |
| 500 | Internal error |

### Background Job — `POST /ocr/parse/jobs`

Upload one file, get a job ID back immediately. Poll `GET /ocr/parse/jobs/{job_id}` for the result later. Use this when the file is large and you do not want to wait.

```bash
# Submit
curl -X POST "http://localhost:8000/ocr/parse/jobs" \
  -H "X-API-Key: sk-local-dev" \
  -F "file=@large_document.pdf"

# Response: {"data": {"job_id": "abc123", "status": "pending", ...}}

# Poll for result
curl -X GET "http://localhost:8000/ocr/parse/jobs/abc123" \
  -H "X-API-Key: sk-local-dev"
```

### Batch — `POST /ocr/parse/batch`

Upload multiple files at once, get a batch ID. Poll `GET /ocr/parse/batch/{batch_id}` for per-file results.

```bash
curl -X POST http://localhost:8000/ocr/parse/batch \
  -H "X-API-Key: sk-local-dev" \
  -F "file=@image1.png" -F "file=@image2.png" -F "file=@document.docx"
```

Each file is processed independently. If one fails, the others still complete. Results expire after 1 hour.

### URL Processing

Convert a web page to text:

```bash
# Sync
curl -X POST "http://localhost:8000/ocr/parse/url" \
  -H "X-API-Key: sk-local-dev" \
  -d "url=https://example.com"

# Background job
curl -X POST "http://localhost:8000/ocr/parse/url/jobs" \
  -H "X-API-Key: sk-local-dev" \
  -d "url=https://example.com"

# Batch (up to 20 URLs)
curl -X POST "http://localhost:8000/ocr/parse/url/batch" \
  -H "X-API-Key: sk-local-dev" \
  -d "url=https://example.com" -d "url=https://example.org"
```

### HTML Processing

Upload an HTML file with optional assets (CSS, images) for rendering:

```bash
curl -X POST "http://localhost:8000/ocr/parse/html" \
  -H "X-API-Key: sk-local-dev" \
  -F "files=@index.html" -F "files=@style.css" -F "files=@logo.png"
```

## URL Safety

The system blocks dangerous URLs to prevent SSRF (Server-Side Request Forgery) attacks — the same kind of protection used by cloud document converters. The following are blocked:

| What | Examples |
|---|---|
| Internal addresses | `localhost`, `127.0.0.1`, `[::1]` |
| Private networks | `10.x.x.x`, `192.168.x.x`, `172.16-31.x.x` |
| Bad schemes | `file://`, `ftp://` — only `http://` and `https://` allowed |
| Blocked domains | Configurable list of forbidden hostnames |

## Important Notes

- **Page images expire after 1 hour** and are automatically cleaned up every 5 minutes
- **Background and batch job results also expire after 1 hour**, cleaned up every 60 seconds
- **Max concurrent jobs:** 2 by default (PaddleOCR is not thread-safe). Can be increased on systems with more CPU cores
- **Office documents** require Gotenberg to be running. Images and PDFs work without it
- **Max file size:** 50MB by default
- **Max batch size:** 20 items
