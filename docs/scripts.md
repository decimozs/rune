# Testing Scripts

Convenience scripts in `scripts/` for automated testing:

| Script | Purpose |
|---|---|
| `test_ocr.sh` | Run OCR on all files in `app/datasets/`, save JSON and Markdown responses to timestamped output dir |
| `benchmark.sh [runs=3] [url] [format=all]` | Run OCR N times per file, print min/max/avg/median timing stats. Filter by format: images, docx, ppt, rtf, csv, xls, xlsx, all |
| `stress.sh [concurrency=5] [url]` | Fire N parallel requests per file, report success rate and RPS |
| `compare_runs.sh [url]` | Run OCR twice, diff outputs (ignoring timestamps), exit 0 if identical |
| `run_test.sh [url]` | Execute full pipeline: parse, benchmark, compare, stress |
| `convert.sh <format> [url]` | Convert datasets to PDF via Gotenberg (formats: docx, ppt, rtf, csv, xls, xlsx, spreadsheet, all) |
| `test_formats.sh [url]` | Test all supported formats (docx, ppt, rtf, csv, xls, xlsx) against OCR endpoint |
| `batch_ocr.sh [url] [poll=2] [format=json] <files...>` | Submit files to batch endpoint, poll until completion, save per-file outputs to `tests/outputs/batch_{id}/` |
| `ocr_batch.sh` | (alias for batch_ocr.sh) |
| `ocr_job.sh [url] [poll=2] [format=json] <file>` | Submit single file to background job endpoint, poll, save result to `tests/outputs/job_{id}/` |
| `cleanup.sh [--older-than N \| --all \| --dry-run]` | List and delete old test output directories with confirmation |

## Examples

```bash
./scripts/test_ocr.sh
./scripts/benchmark.sh 5
./scripts/benchmark.sh 3 http://localhost:8000 docx    # benchmark only docx
./scripts/stress.sh 10
./scripts/compare_runs.sh
./scripts/convert.sh docx
./scripts/convert.sh spreadsheet
./scripts/convert.sh all
./scripts/test_formats.sh
./scripts/run_test.sh
./scripts/batch_ocr.sh http://localhost:8000 2 json app/datasets/images/*.png
./scripts/ocr_job.sh http://localhost:8000 2 markdown app/datasets/docx/sample1.docx
./scripts/cleanup.sh --older-than 7
```

All scripts check that the server is running before proceeding.
