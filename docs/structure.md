# Project Structure

```
app/
├── main.py               # FastAPI app entrypoint, lifespan, exception handlers
├── config.py             # pydantic-settings config (OCR_ env vars)
├── routes/
│   └── ocr.py            # OCR endpoints: sync parse, async jobs, async batch
├── services/
│   ├── ocr.py            # Orchestrator (composes engine, formatter, markdown)
│   ├── engine.py         # PaddleOCR + PPStructureV3 model init & prediction
│   ├── formatter.py      # Raw OCR output → structured JSON
│   ├── markdown.py       # PPStructureV3 markdown conversion + image saving
│   ├── converter.py      # Gotenberg document-to-PDF conversion
│   ├── batch.py          # Batch processor: in-memory queue, per-file isolation, 1hr TTL
│   ├── background.py     # Background job processor: single-file async with TTL cleanup
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

docker-compose.yml        # API + Gotenberg services

scripts/                  # Automation & testing scripts
├── test_ocr.sh
├── benchmark.sh
├── stress.sh
├── compare_runs.sh
├── convert.sh
├── run_test.sh
├── test_formats.sh
├── batch_ocr.sh          # Submit files to batch endpoint, poll, save per-file outputs
├── ocr_batch.sh          # (alias for batch_ocr.sh)
├── ocr_job.sh            # Submit single file to background job endpoint, poll, save output
└── cleanup.sh

tests/
└── outputs/              # Test script output directories (auto-created, gitignored)
```
