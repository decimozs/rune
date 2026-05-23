# API Reference

OCR endpoints are prefixed with `/ocr`. Health endpoints (`/health`, `/health/ready`) are root-level.

Three source types are supported:
- **File** — upload images, PDFs, and office documents directly
- **URL** — provide URLs; Gotenberg Chromium fetches and renders pages to PDF, then OCR processes the PDF
- **HTML** — upload `index.html` plus optional assets (CSS, images); Gotenberg Chromium renders to PDF, then OCR processes the PDF

> **⚠️ Gotenberg required** for office documents (DOC, DOCX, PPT, PPTX, RTF, CSV, XLS, XLSX), URL sources, and HTML sources. Image/PDF uploads work without Gotenberg.

---

## `GET /health`

Liveness probe — always returns `200` if the application is running. Use for Docker `HEALTHCHECK`.

**Response (200):**
```json
{
  "status": "ok"
}
```

**cURL:**
```bash
curl http://localhost:8000/health
```

---

## `GET /health/ready`

Readiness probe — returns `200` if all dependencies are initialized (OCR engine, structure engine). Returns `503` if any dependency is not ready. Use for container orchestration readiness checks (e.g., k8s `readinessProbe`).

**Response (200):**
```json
{
  "status": "ok",
  "checks": {
    "ocr_engine": "ok",
    "structure_engine": "ok"
  }
}
```

**Response (503 — degraded):**
```json
{
  "detail": {
    "status": "degraded",
    "checks": {
      "ocr_engine": "fail",
      "structure_engine": "ok"
    }
  }
}
```

**cURL:**
```bash
curl http://localhost:8000/health/ready
```

---

## `POST /ocr/parse`

Synchronous endpoint — blocks until OCR completes. For non-blocking alternatives, see [`POST /ocr/parse/jobs`](#post-ocrparsejobs) (single file) or [`POST /ocr/parse/batch`](#post-ocrparsebatch) (multiple files).

Upload an image, PDF, or office document for OCR extraction. Office documents (DOC, DOCX, PPT, PPTX, RTF, CSV, XLS, XLSX) are automatically converted to PDF via Gotenberg (LibreOffice) before processing.

**Query Parameters:**
- `format` — `json` (default), `markdown`, or `xml`

**Request:** `multipart/form-data` with field `file`

**Allowed MIME types:**

| Category | MIME Type | Format |
|---|---|---|
| Image | `image/jpeg` | JPEG |
| Image | `image/png` | PNG |
| Image | `image/bmp` | BMP |
| Image | `image/tiff` | TIFF |
| Image | `image/webp` | WebP |
| Document | `application/pdf` | PDF |
| Document | `application/msword` | DOC |
| Document | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | DOCX |
| Presentation | `application/vnd.ms-powerpoint` | PPT |
| Presentation | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | PPTX |
| Document | `text/rtf` | RTF |
| Spreadsheet | `text/csv` | CSV |
| Spreadsheet | `application/vnd.ms-excel` | XLS |
| Spreadsheet | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | XLSX |

**Validation:** Content-Type header checked against allowed list. Images and PDFs also verified via `python-magic` MIME sniffing. Office documents forwarded to Gotenberg (server-side validation).

**cURL (JSON — image):**

```bash
curl -X POST http://localhost:8000/ocr/parse \
  -F "file=@path/to/image.png"
```

**cURL (Markdown — office document):**

```bash
curl -X POST "http://localhost:8000/ocr/parse?format=markdown" \
  -F "file=@path/to/document.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document"
```

**cURL (XML):**

```bash
curl -X POST "http://localhost:8000/ocr/parse?format=xml" \
  -F "file=@path/to/image.png"
```

**Markdown mode:** Returns extracted markdown with images saved to `app/outputs/imgs/` and paths rewritten to `/assets/imgs/...`. Access images at `http://localhost:8000/assets/imgs/...`.

**XML mode:** Returns OCR result as pretty-printed XML string in the `data` field.

**CORS:** Endpoints allow `*` origin for internal demo access (e.g., `file://` origins from the standalone frontend).

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
        "extracted_text": "Hello World",
        "page_image_url": "/assets/pages/a1b2c3d4e5f6/page_1.png",
        "ocr_width": 1200,
        "ocr_height": 1600
      }
    ]
  }
}
```

**Success Response — XML (200):**

```json
{
  "success": true,
  "metadata": {
    "timestamp": "2026-05-21T12:00:00Z",
    "model": "PP-OCRv4",
    "format": "xml",
    "processing_time_ms": 123.45,
    "file_name": "image.png",
    "file_type": "image/png"
  },
  "data": "<?xml version=\"1.0\" ?>\n<ocrResult>\n  <page number=\"1\">\n    <words>\n      <word confidence=\"0.9876\">\n        <text>Hello World</text>\n        <bbox>\n          <point x=\"10\" y=\"20\"/>\n          <point x=\"100\" y=\"20\"/>\n          <point x=\"100\" y=\"40\"/>\n          <point x=\"10\" y=\"40\"/>\n        </bbox>\n      </word>\n    </words>\n    <extractedText>Hello World</extractedText>\n  </page>\n</ocrResult>"
}
```

**Error Responses:**

| Status | Code | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing filename |
| 404 | `NOT_FOUND` | Batch or job ID not found |
| 413 | `FILE_TOO_LARGE` | Exceeds `OCR_MAX_FILE_SIZE` |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | MIME type not in allowed list |
| 502 | `CONVERSION_ERROR` | Gotenberg document conversion failed |
| 500 | `OCR_ERROR` | Engine processing failure |
| 500 | `INTERNAL_ERROR` | Unhandled exception |

Errors are per-file isolated in batch/background jobs — one failure does not affect other files. Background jobs report errors inline when polled, not via HTTP status codes.

```json
{
  "success": false,
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "Unsupported file type: image/gif. Allowed: image/jpeg, image/png, ..."
  }
}
```

---

## `POST /ocr/parse/batch`

Upload multiple files for asynchronous batch processing. Returns immediately with a `batch_id`. Poll `GET /ocr/parse/batch/{batch_id}` for status and per-file results.

**Query Parameters:**
- `format` — `json` (default), `markdown`, or `xml`

**cURL:**
```bash
curl -X POST http://localhost:8000/ocr/parse/batch \
  -F "file=@image1.png" -F "file=@image2.png" -F "file=@document.docx"
```

**Response (202):**
```json
{
  "success": true,
  "metadata": { "timestamp": "...", "model": "PP-OCRv4", "format": "json" },
  "data": {
    "batch_id": "a1b2c3d4e5f6",
    "status": "pending",
    "total_files": 3,
    "created_at": "2026-05-21T12:00:00+00:00"
  }
}
```

---

## `GET /ocr/parse/batch/{batch_id}`

Poll batch job status. Returns per-file results once all files complete.

**Response (completed):**
```json
{
  "success": true,
  "data": {
    "batch_id": "a1b2c3d4e5f6",
    "status": "completed",
    "total_files": 3,
    "completed": 2,
    "failed": 1,
    "processing_time_ms": 8450.23,
    "items": [
      {
        "file_name": "image1.png",
        "file_type": "image/png",
        "processing_time_ms": 1230.45,
        "success": true,
        "data": { "pages": [...] }
      },
      {
        "file_name": "broken.doc",
        "file_type": "application/msword",
        "processing_time_ms": 520.10,
        "success": false,
        "error": { "code": "ValueError", "message": "Unsupported type: ..." }
      }
    ]
  }
}
```

Batch results expire after 1 hour and are cleaned up automatically on a 60s interval.

---

## `POST /ocr/parse/jobs`

Upload a single file for asynchronous background processing. Like `/ocr/parse` but non-blocking — returns a `job_id` immediately. Poll `GET /ocr/parse/jobs/{job_id}` for the result.

**Query Parameters:**
- `format` — `json` (default), `markdown`, or `xml`

**cURL:**
```bash
curl -X POST "http://localhost:8000/ocr/parse/jobs?format=json" \
  -F "file=@image.png"
```

**Response (202):**
```json
{
  "success": true,
  "metadata": { "timestamp": "...", "model": "PP-OCRv4", "format": "json" },
  "data": {
    "job_id": "a1b2c3d4e5f6",
    "status": "pending",
    "file_name": "image.png",
    "file_type": "image/png",
    "created_at": "2026-05-21T12:00:00+00:00"
  }
}
```

---

## `GET /ocr/parse/jobs/{job_id}`

Poll a background job. Returns the OCR result when complete.

**Response (completed):**
```json
{
  "success": true,
  "metadata": { "timestamp": "...", "model": "PP-OCRv4", "format": "json" },
  "data": {
    "job_id": "a1b2c3d4e5f6",
    "status": "completed",
    "file_name": "image.png",
    "file_type": "image/png",
    "created_at": "...",
    "completed_at": "...",
    "processing_time_ms": 1230.45,
    "data": { "pages": [...] }
  }
}
```

**Response (failed):**
```json
{
  "success": true,
  "data": {
    "job_id": "a1b2c3d4e5f6",
    "status": "failed",
    "error": { "code": "ValueError", "message": "Unsupported type: ..." }
  }
}
```

Jobs expire after 1 hour and are cleaned up automatically on a 60s interval.

---

## `POST /ocr/parse/url`

Synchronous — convert a URL to PDF via Gotenberg Chromium, then OCR the result.

**Query Parameters:**
- `format` — `json` (default), `markdown`, or `xml`

**Request:** `application/x-www-form-urlencoded` with field `url`

**cURL:**
```bash
curl -X POST "http://localhost:8000/ocr/parse/url?format=json" \
  -d "url=https://example.com"
```

**Errors:** Same error codes as `/ocr/parse`. Plus `CONVERSION_ERROR` (502) if Gotenberg cannot fetch or render the URL.

---

## `POST /ocr/parse/url/jobs`

Background job — same as `/ocr/parse/url` but returns a `job_id` immediately.

**cURL:**
```bash
curl -X POST "http://localhost:8000/ocr/parse/url/jobs?format=json" \
  -d "url=https://example.com"
```

**Response (202):** Same structure as `/ocr/parse/jobs`.

---

## `POST /ocr/parse/url/batch`

Batch — submit up to 20 URLs. Each URL is independently converted and OCR'd.

**cURL:**
```bash
curl -X POST "http://localhost:8000/ocr/parse/url/batch?format=json" \
  -d "url=https://example.com" -d "url=https://example.org"
```

**Response (202):** Same structure as `/ocr/parse/batch`.

---

## `POST /ocr/parse/html`

Synchronous — upload an HTML file (plus optional assets) for Chromium rendering → PDF → OCR.

**Query Parameters:**
- `format` — `json` (default), `markdown`, or `xml`

**Request:** `multipart/form-data` with field `files`. At minimum include `index.html`:

```bash
curl -X POST "http://localhost:8000/ocr/parse/html?format=json" \
  -F "files=@index.html" -F "files=@style.css" -F "files=@logo.png"
```

**Notes:**
- Assets (CSS, JS, images) are referenced by filename only — no subdirectories
- CDN URLs work for external resources
- Any `.html`/`.htm` file is renamed to `index.html` before sending to Gotenberg

**Errors:** Same error codes as `/ocr/parse`. Plus `CONVERSION_ERROR` (502) if Gotenberg cannot render the HTML.

---

## `POST /ocr/parse/html/jobs`

Background job — same as `/ocr/parse/html` but returns a `job_id` immediately.

**cURL:**
```bash
curl -X POST "http://localhost:8000/ocr/parse/html/jobs?format=json" \
  -F "files=@index.html" -F "files=@style.css"
```

**Response (202):** Same structure as `/ocr/parse/jobs`.

---

## `POST /ocr/parse/html/batch`

Batch — upload multiple HTML file sets. Each `.html`/`.htm` file starts a new batch item; subsequent assets (CSS, images, etc.) attach to the preceding HTML item until the next `.html`/`.htm` file.

**cURL:**
```bash
curl -X POST "http://localhost:8000/ocr/parse/html/batch?format=json" \
  -F "files=@page1.html" -F "files=@page1.css" \
  -F "files=@page2.html" -F "files=@page2.css"
```

**Response (202):** Same structure as `/ocr/parse/batch`.

---

## Limitations & Warnings

| Issue | Warning |
|---|---|
| **Gotenberg dependency** | Office docs, URL, and HTML sources require Gotenberg. Without it these return `CONVERSION_ERROR` (502). Image and PDF uploads work independently. |
| **Gotenberg URL routing** | `.env` uses `http://localhost:3000` (local dev). `docker-compose.yml` overrides to `http://gotenberg:3000` (Docker DNS). Set `OCR_GOTENBERG_URL` if a custom address is needed. |
| **Gotenberg Chromium rendering** | URL and HTML conversions use Gotenberg's Chromium sub-process. Complex client-side JavaScript SPAs may not render fully (Gotenberg waits for network idle but has a default 30s timeout). |
| **HTML assets** | Only filename references — not subdirectory paths. All assets must be in the same upload; external CDN URLs are safe. |
| **Max file size** | Default 50MB (`OCR_MAX_FILE_SIZE`). Larger files return 413. |
| **Max batch size** | 20 items per batch (`MAX_BATCH_SIZE`). |
| **Concurrent OCR limit** | `OCR_MAX_CONCURRENT_JOBS` (default 2) limits parallel PaddleOCR calls. Reduce for low-memory systems. |
| **PaddleOCR PDF rendering** | PaddleOCR internally uses `pdftoppm` (poppler-utils) at 200 DPI. Page images are captured from PaddleOCR's `doc_preprocessor_res["output_img"]` to guarantee bbox alignment. |
| **`use_doc_unwarping=False`** | Disables PaddleOCR's DocPreprocessor unwarping and orientation classification. Bbox coordinates match the original rendered page image. Do not enable unless you understand the coordinate space implications. |
| **Output TTL** | Page images and markdown assets expire after 1 hour (`OCR_OUTPUT_TTL`). Sweep runs every 5 minutes. |
| **Batch/job TTL** | Batch and background job results expire after 1 hour. Cleanup runs every 60 seconds. |
