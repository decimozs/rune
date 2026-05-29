# Configuration

All settings are configured through environment variables or a `.env` file. Each variable starts with `OCR_`.

## Core Settings

| Variable | Default | What It Does |
|---|---|---|
| `OCR_LANG` | `en` | Language for text recognition |
| `OCR_VERSION` | `PP-OCRv4` | Default PaddleOCR model version |
| `OCR_MODELS` | `PP-OCRv4` | Comma-separated list of model versions to pre-load at startup (e.g. `PP-OCRv4,PP-OCRv5`). Each loaded model uses ~300MB RAM |
| `OCR_ENABLE_MKLDNN` | `false` | Intel CPU acceleration (faster on supported hardware) |
| `OCR_USE_TEXTLINE_ORIENTATION` | `true` | Detect if text is rotated |

## File Processing

| Variable | Default | What It Does |
|---|---|---|
| `OCR_MAX_FILE_SIZE` | `52428800` (50MB) | Maximum upload size in bytes |
| `OCR_UPLOAD_DIR` | `/tmp` | Temporary folder for uploaded files |
| `OCR_ALLOWED_CONTENT_TYPES` | _(long list)_ | Which file types are accepted |
| `OCR_GOTENBERG_URL` | `http://localhost:3000` | Address of Gotenberg document converter |
| `OCR_MAX_CONCURRENT_JOBS` | `2` | How many files to process at the same time |

## Output

| Variable | Default | What It Does |
|---|---|---|
| `OCR_OUTPUT_DIR` | `app/outputs` | Where to save page images and markdown files |
| `OCR_OUTPUT_TTL` | `3600` (1 hour) | How long output files live before cleanup |
| `OCR_ASSET_BASE_URL` | _(empty)_ | Base URL for image URLs in responses. Set to `http://localhost:8080` when using Docker with nginx, leave empty for local dev |

## Authentication

| Variable | Default | What It Does |
|---|---|---|
| `OCR_API_KEYS` | `#` (disabled) | API keys in `key=name` format. `#` disables auth |
| `OCR_DB_PATH` | _(empty)_ | Path to SQLite database for storing API keys. When set, keys are stored as secure hashes |

## URL Safety

| Variable | Default | What It Does |
|---|---|---|
| `OCR_URL_MAX_LENGTH` | `2048` | Maximum URL length for `/ocr/parse/url` |
| `OCR_URL_BLOCKED_DOMAINS` | _(empty)_ | Domains to always block (comma-separated) |
| `OCR_URL_ALLOWED_DOMAINS` | _(empty)_ | Domains to allow (comma-separated) |
| `OCR_COMPANY_DOMAINS_ONLY` | `false` | If `true`, only domains in `OCR_URL_ALLOWED_DOMAINS` are accepted |

## Logging

| Variable | Default | What It Does |
|---|---|---|
| `OCR_LOG_LEVEL` | `INFO` | How detailed logs should be: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `OCR_LOG_FORMAT` | `text` | Log output format: `text` (human-readable) or `json` (structured for log aggregators) |

## How to Configure

Create a `.env` file in the project root (see `.env.example` for a template):

```bash
OCR_LANG=en
OCR_MAX_FILE_SIZE=104857600
OCR_API_KEYS=sk-my-key=admin
```

Or set environment variables directly:

```bash
export OCR_LANG=ja
export OCR_MAX_FILE_SIZE=104857600
```

When using Docker Compose, settings go in the `environment:` section of `docker-compose.yml` or in the `env_file: .env` reference. Docker Compose overrides the `OCR_GOTENBERG_URL` to `http://gotenberg:3000` (using Docker's internal DNS).
