# Testing

## Unit Tests (pytest)

Fast unit tests covering schemas, formatter, XML output, converter, and processor logic — no PaddleOCR required.

```bash
make test          # or: uv run pytest tests/ -v
```

## Integration Scripts

Convenience scripts in `scripts/` for automated integration testing:

| Script | Purpose |
|---|---|
| `benchmark.sh [runs=3] [url] [format=all] [--parallel N] [--json] [--sort=avg\|name\|size]` | Run OCR N times per file, print enhanced stats (min/max/avg/median/p90/p95/p99/stddev/file size/category). Supports parallel execution (`--parallel N`), machine-readable output (`--json`), and sorting (`--sort`). Filter by format: images, docx, ppt, rtf, csv, xls, xlsx, all |
| `stress.sh [concurrency=5] [url]` | Fire N parallel requests per file, report success rate and RPS |
| `convert.sh <format> [url]` | Convert datasets to PDF via Gotenberg (formats: docx, ppt, rtf, csv, xls, xlsx, spreadsheet, all) |
| `test_formats.sh [url]` | Test all supported formats (docx, ppt, rtf, csv, xls, xlsx) against OCR endpoint |
| `batch_ocr.sh [url] [poll=2] [format=json] <files...>` | Submit files to batch endpoint, poll until completion, save per-file outputs to `tests/outputs/batch_{id}/` |
| `ocr_job.sh [url] [poll=2] [format=json] <file>` | Submit single file to background job endpoint, poll, save result to `tests/outputs/job_{id}/` |
| `test_routes.sh [url] [timeout=60]` | Test all routes (health, sync, jobs, batch, URL, HTML, edge cases), validate response structure, exit non-zero on failure |
| `parallel_ocr.sh [url] [poll=2] [format=json] <files...>` | Submit each file as individual background job in one burst, poll all concurrently, progressive output |
| `cleanup.sh [--older-than N \| --all \| --dry-run]` | List and delete old test output directories with confirmation |
| `test_auth.sh [url] [key]` | Test API key auth flow: probe mode, missing/wrong/valid key, GET protection, health open |
| `create_api_key.py --name <name> [--team <team>] [--db-path <path>]` | Generate a new `sk_live_*` API key and store SHA-256 hash in SQLite |
| `list_api_keys.py [--db-path <path>]` | List all API keys (prefix, name, team, active, created/last-used/revoked dates) |
| `revoke_api_key.py --prefix <prefix> [--db-path <path>]` | Revoke an active API key by prefix (sets `is_active=0`) |

## Examples

```bash
./scripts/benchmark.sh 5                                 # sequential, 5 runs
./scripts/benchmark.sh 3 http://localhost:8000 docx      # benchmark only docx
./scripts/benchmark.sh 3 localhost:8000 all --parallel 4  # 4 concurrent files
./scripts/benchmark.sh --json                            # machine-readable output
./scripts/stress.sh 10
./scripts/convert.sh docx
./scripts/convert.sh spreadsheet
./scripts/convert.sh all
./scripts/test_formats.sh
./scripts/batch_ocr.sh http://localhost:8000 2 json app/datasets/images/*.png
./scripts/ocr_job.sh http://localhost:8000 2 markdown app/datasets/docx/sample1.docx
./scripts/test_routes.sh
./scripts/test_routes.sh http://localhost:8000 120   # longer async timeout
./scripts/parallel_ocr.sh http://localhost:8000 2 json app/datasets/images/*.png app/datasets/docx/*.docx
./scripts/cleanup.sh --older-than 7
./scripts/test_auth.sh http://localhost:8000              # probe auth mode, test basic flow
./scripts/test_auth.sh http://localhost:8000 sk_live_abc   # test with a specific key

# Key management (DB auth mode)
uv run python scripts/create_api_key.py --name marlon --team engineering --db-path app/data/ocr.db
uv run python scripts/list_api_keys.py --db-path app/data/ocr.db
uv run python scripts/revoke_api_key.py --prefix sk_live_AbCdEf --db-path app/data/ocr.db
```

All shell scripts check that the server is running before proceeding.
