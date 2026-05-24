# Project Structure

```
app/
├── main.py               # FastAPI app entrypoint, lifespan, exception handlers
├── config.py             # pydantic-settings config (OCR_ env vars)
├── routes/
│   ├── ocr.py            # OCR endpoints: sync parse, async jobs, async batch
│   └── health.py         # Health check endpoints: /health, /health/ready
├── outputs/
│   ├── imgs/              # Extracted markdown images (served at /assets/imgs/)
│   └── pages/             # Per-page OCR images grouped by stem (served at /assets/pages/)
├── services/
│   ├── ocr.py            # Orchestrator (composes engine, formatter, markdown)
│   ├── engine.py         # PaddleOCR + PPStructureV3 model init & prediction
│   ├── formatter.py      # Raw OCR output → structured JSON
│   ├── xml_formatter.py  # OCRResult dict → pretty-printed XML
│   ├── markdown.py       # PPStructureV3 markdown conversion + image saving
│   ├── converter.py      # Gotenberg document-to-PDF conversion via LibreOffice + Chromium URL/HTML (reused httpx client)
│   ├── processor.py      # Shared file pipeline: write → magic → convert → OCR → cleanup
│   ├── batch.py          # Batch processor: in-memory queue, per-file isolation, 1hr TTL
│   ├── background.py     # Background job processor: single-file async with TTL cleanup
│   ├── auth.py           # API key verification FastAPI dependency
│   ├── url_guard.py      # SSRF-safe URL validation (scheme, private IPs, DNS, domain lists)
│   ├── cleanup.py        # Output file sweeper (page images, markdown assets)
│   └── exceptions.py     # Custom exceptions (OCRValidationError, OCRRuntimeError)
├── schemas/
│   ├── ocr.py            # Domain models: BoundingBox, WordBlock, OCRPage, SingleJobStatus, BatchItemResult, BatchStatus
│   └── response.py       # API envelope: APIResponse, ResponseMetadata, ErrorDetail
└── datasets/             # Sample files for testing
    ├── images/           # PNG, JPG test files
    ├── docx/
    ├── ppt/
    ├── rtf/
    └── spreadsheets/     # CSV, XLS, XLSX

Makefile                  # Common task automation (dev, Docker, scripts)

index.html                # Standalone demo frontend (drag-and-drop, 3 modes, JSON/MD/XML/Visualize with bbox overlays, pdf.js fallback, IntersectionObserver lazy-loading)

docker-compose.yml        # API + Gotenberg services (healthchecks, env_file)

scripts/                  # Automation & testing scripts
├── benchmark.sh          # Enhanced stats, parallel mode (--parallel N), JSON output
├── stress.sh
├── convert.sh
├── test_formats.sh
├── batch_ocr.sh          # Submit files to batch endpoint, poll, save per-file outputs
├── ocr_job.sh            # Submit single file to background job endpoint, poll, save output
├── test_routes.sh        # Validate all routes (health, sync, jobs, batch, edge cases)
├── parallel_ocr.sh       # Burst-submit individual background jobs, poll all concurrently
└── cleanup.sh

tests/
└── outputs/              # Test script output directories (auto-created, gitignored)
```
