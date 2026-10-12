# Testing Tools

## Unit Tests

Fast unit tests that do not need PaddleOCR models:

```bash
make test
# or
uv run pytest tests/ -v
```

## Integration Testing Scripts

Convenience scripts in `scripts/` for testing the running API:

| Script | What It Does |
|---|---|
| `test_routes.sh` | Tests all API routes — health, sync OCR, jobs, batch, URL, HTML, edge cases. Exits with error if anything fails |
| `test_formats.sh` | Tests all supported file formats (DOCX, PPT, RTF, CSV, XLS, XLSX) |
| `test_auth.sh` | Tests API key authentication — missing key, wrong key, valid key, protected endpoints |
| `benchmark.sh` | Runs OCR on each file multiple times, reports min/max/average/median speeds |
| `stress.sh` | Sends many requests at the same time to test server load handling |
| `batch_ocr.sh` | Submits files to the batch endpoint, waits for completion, saves per-file results |
| `ocr_job.sh` | Submits a single file to the background job endpoint, waits, saves the result |
| `parallel_ocr.sh` | Submits many individual background jobs at once, polls all of them |
| `convert.sh` | Converts office documents to PDF via Gotenberg |
| `cleanup.sh` | Deletes old test output files |

### Key Management Scripts (DB Auth Mode)

| Script | What It Does |
|---|---|
| `create_api_key.py` | Generates a new `sk_live_*` API key and stores its secure hash in the database |
| `list_api_keys.py` | Lists all API keys with name, team, active status, and dates |
| `revoke_api_key.py` | Revokes an API key by its prefix |

### Examples

```bash
# Run a quick benchmark on all file types
./scripts/benchmark.sh 3

# Test with 4 files at the same time
./scripts/benchmark.sh 3 http://localhost:8000 all --parallel 4

# Submit files to batch, poll every 2 seconds
./scripts/batch_ocr.sh http://localhost:8000 2 json app/datasets/images/*.png

# Create a new API key
uv run python scripts/create_api_key.py \
  --name alice --team engineering --db-path app/data/ocr.db

# List all API keys
uv run python scripts/list_api_keys.py --db-path app/data/ocr.db
```

All shell scripts check the server is running before starting.
