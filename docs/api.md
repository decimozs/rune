# API Reference

OCR endpoints are prefixed with `/ocr`. Health endpoints (`/health`, `/health/ready`) are root-level.

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

Upload an image, PDF, or office document for OCR extraction. Office documents (DOCX, PPT, RTF, CSV, XLS, XLSX) are automatically converted to PDF via Gotenberg before processing.

**Query Parameters:**
- `format` — `json` (default) or `markdown`

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
- `format` — `json` (default) or `markdown`

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
- `format` — `json` (default) or `markdown`

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
