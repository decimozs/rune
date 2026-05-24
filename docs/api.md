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
- `include_bbox` — bool, default `true`. Include bbox coordinates in JSON output (JSON format only)
- `include_confidence` — bool, default `true`. Include confidence scores in JSON output (JSON format only)
- `include_extracted_text` — bool, default `true`. Include extracted text in JSON output (JSON format only)
- `include_page_image` — bool, default `true`. Include page image URLs in JSON output (JSON format only)

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

**cURL (JSON — exclude bbox and page image):**

```bash
curl -X POST "http://localhost:8000/ocr/parse?include_bbox=false&include_page_image=false" \
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

> **JSON output options** (`include_bbox`, `include_confidence`, `include_extracted_text`, `include_page_image`) only affect `format=json`. Setting any to `false` strips the corresponding field from the response. Markdown and XML output always include all data and ignore these params.

**Success Response — default JSON (200):**

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

**Success Response — JSON with `include_bbox=false&include_confidence=false&include_page_image=false`:**

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
          { "text": "Hello World" }
        ],
        "extracted_text": "Hello World"
      }
    ]
  }
}
```

Note: `exclude_none=true` strips null fields. When `page_image_url` is excluded, the field is absent rather than `null`.

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
- `include_bbox` — bool, default `true` (JSON only)
- `include_confidence` — bool, default `true` (JSON only)
- `include_extracted_text` — bool, default `true` (JSON only)
- `include_page_image` — bool, default `true` (JSON only)

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
- `include_bbox` — bool, default `true` (JSON only)
- `include_confidence` — bool, default `true` (JSON only)
- `include_extracted_text` — bool, default `true` (JSON only)
- `include_page_image` — bool, default `true` (JSON only)

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
- `include_bbox` — bool, default `true` (JSON only)
- `include_confidence` — bool, default `true` (JSON only)
- `include_extracted_text` — bool, default `true` (JSON only)
- `include_page_image` — bool, default `true` (JSON only)

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

Accepts same query params as `/ocr/parse/url` (`include_bbox`, `include_confidence`, `include_extracted_text`, `include_page_image`).

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
- `include_bbox` — bool, default `true` (JSON only)
- `include_confidence` — bool, default `true` (JSON only)
- `include_extracted_text` — bool, default `true` (JSON only)
- `include_page_image` — bool, default `true` (JSON only)

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

Accepts same query params as `/ocr/parse/html` (`include_bbox`, `include_confidence`, `include_extracted_text`, `include_page_image`).

**cURL:**
```bash
curl -X POST "http://localhost:8000/ocr/parse/html/batch?format=json" \
  -F "files=@page1.html" -F "files=@page1.css" \
  -F "files=@page2.html" -F "files=@page2.css"
```

**Response (202):** Same structure as `/ocr/parse/batch`.

---

---

## Authentication

Auth mode depends on config:

| Config | Auth mode | Key storage |
|---|---|---|
| `OCR_API_KEYS=#` (default), no `OCR_DB_PATH` | **Disabled** — no header required | — |
| `OCR_API_KEYS=key=name,...`, no `OCR_DB_PATH` | **Env-var** — keys read from `.env` | Plaintext in env, restart required to change |
| `OCR_DB_PATH=app/data/ocr.db` | **DB-backed** — keys stored hashed in SQLite | SHA-256 hash, no restart needed for new/revoked keys |

### DB-backed auth (recommended)

Set `OCR_DB_PATH` in `.env`. Keys are stored as SHA-256 hashes. Auto-migrates `OCR_API_KEYS` entries on first startup if the key table is empty.

```bash
# Create a key
uv run python scripts/create_api_key.py --name marlon --team engineering --db-path app/data/ocr.db
# Output: API key: sk_live_AbCdEf...

# Test it
curl -X POST http://localhost:8000/ocr/parse \
  -H "X-API-Key: sk_live_AbCdEf..." \
  -F "file=@image.png"
```

New keys work **immediately** — no server restart.

### Env-var auth (legacy)

When `OCR_API_KEYS` is set in `.env` (default `#` = disabled) and `OCR_DB_PATH` is empty:

```bash
curl -X POST http://localhost:8000/ocr/parse \
  -H "X-API-Key: sk-prod-abc123" \
  -F "file=@image.png"
```

Key format: `key=name` pairs for audit identity. Example: `OCR_API_KEYS=sk-abc=alice,sk-def=bob`. The dependency returns the key name (or `"unknown"` for bare keys).

### Protected endpoints

All POST endpoints **require** `X-API-Key` header when auth is enabled:
`/ocr/parse`, `/ocr/parse/jobs`, `/ocr/parse/batch`, `/ocr/parse/url`, `/ocr/parse/url/jobs`, `/ocr/parse/url/batch`, `/ocr/parse/html`, `/ocr/parse/html/jobs`, `/ocr/parse/html/batch`

GET endpoints also **require** `X-API-Key` when auth is enabled:
`/ocr/parse/jobs/{id}`, `/ocr/parse/batch/{id}`

Health endpoints (`/health`, `/health/ready`) are always open.

### Error response (401)

```json
{
  "error": {
    "code": "http_error",
    "message": "Invalid API key"
  }
}
```

### CLI key management

| Script | Purpose |
|---|---|
| `scripts/create_api_key.py --name <name> --db-path <path>` | Generate a new `sk_live_*` key, store hash in SQLite |
| `scripts/list_api_keys.py --db-path <path>` | List all keys with prefix, name, team, active status, dates |
| `scripts/revoke_api_key.py --prefix <prefix> --db-path <path>` | Revoke a key (set `is_active=0`) |

---

## URL Safety

URL and HTML source endpoints enforce security checks to prevent SSRF and internal network access:

| Check | Behavior |
|---|---|
| **Scheme** | Only `http://` and `https://` allowed. `file://`, `ftp://`, `data://` rejected. |
| **Loopback** | `localhost`, `127.0.0.1`, `[::1]`, `0.0.0.0` rejected by string + DNS resolution. |
| **Private IPs** | `10.x.x.x`, `172.16.x.x`–`172.31.x.x`, `192.168.x.x` rejected. |
| **Link-local** | `169.254.x.x` rejected. |
| **Broadcast** | `255.255.255.255` rejected. |
| **DNS resolution** | Hostnames are resolved and the resolved IP is checked. DNS-to-private-IP (e.g., `internal.corp` → `10.0.0.5`) is blocked. |
| **Max URL length** | Default 2048 characters (`OCR_URL_MAX_LENGTH`). |
| **Blocked domains** | `OCR_URL_BLOCKED_DOMAINS` — exact hostname match. |
| **Company-only mode** | `OCR_COMPANY_DOMAINS_ONLY=true` restricts to domains in `OCR_URL_ALLOWED_DOMAINS` (prefix/subdomain match). |

Validation runs before any network call to Gotenberg. Errors return **400** with code `validation_error`.

```bash
# Blocked: localhost
curl -X POST "http://localhost:8000/ocr/parse/url" \
  -d "url=http://localhost:8080/admin"

# Blocked: private IP
curl -X POST "http://localhost:8000/ocr/parse/url" \
  -d "url=http://192.168.1.1/dashboard"

# Blocked: bad scheme
curl -X POST "http://localhost:8000/ocr/parse/url" \
  -d "url=file:///etc/passwd"
```

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
| **JSON output options** | `include_bbox`, `include_confidence`, `include_extracted_text`, `include_page_image` only affect `format=json`. Markdown and XML always include all fields. Setting any `include_*` to `false` strips the field from the JSON response entirely (not set to `null`). |
| **Auth (env-var)** | Set `OCR_API_KEYS` in `.env` (comma-separated, format `key=name`). When set, all POST + GET job/batch endpoints require `X-API-Key` header. Default `#` disables auth. Restart required to add/revoke keys. |
| **Auth (DB)** | Set `OCR_DB_PATH=app/data/ocr.db` in `.env`. Keys stored as SHA-256 hashes in SQLite. Use `scripts/create_api_key.py` to generate keys. New keys work immediately — no restart. |
| **GET auth** | `GET /ocr/parse/jobs/{id}` and `GET /ocr/parse/batch/{id}` now require `X-API-Key` when auth is enabled. Health endpoints remain open. |
| **URL safety** | URL endpoints validate scheme (http/https only), block private IP ranges (10.x, 172.16-31.x, 192.168.x), loopback (localhost, 127.x.x.x), link-local (169.254.x.x), metadata IPs (0.x.x.x). DNS resolution checks prevent SSRF. See `OCR_URL_BLOCKED_DOMAINS`, `OCR_URL_ALLOWED_DOMAINS`, `OCR_COMPANY_DOMAINS_ONLY`. |
