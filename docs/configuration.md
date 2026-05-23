# Configuration

Settings loaded from `.env` file (see `.env.example`) or environment variables with `OCR_` prefix:

| Variable | Default | Description |
|---|---|---|
| `OCR_LANG` | `en` | OCR language code |
| `OCR_VERSION` | `PP-OCRv4` | PaddleOCR model version |
| `OCR_ENABLE_MKLDNN` | `false` | Intel MKL-DNN CPU acceleration |
| `OCR_USE_TEXTLINE_ORIENTATION` | `true` | Detect textline orientation |
| (hardcoded) | `use_doc_unwarping=False` | Disable PaddleOCR DocPreprocessor unwarping to keep bbox coords in original image space |
| `OCR_OUTPUT_TTL` | `3600` | Seconds before old page images / markdown assets are cleaned |
| `OCR_MAX_CONCURRENT_JOBS` | `2` | Max concurrent OCR calls across background + batch processors |
| `OCR_MAX_FILE_SIZE` | `52428800` | Max upload size (bytes, ~50MB) |
| `OCR_UPLOAD_DIR` | `/tmp` | Temp directory for uploads |
| `OCR_ALLOWED_CONTENT_TYPES` | `image/jpeg,image/png,image/bmp,image/tiff,image/webp,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/rtf,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Comma-separated allowed MIME types. Any `.env` override replaces the entire list. |
| `OCR_OUTPUT_DIR` | `app/outputs` | Markdown output directory |
| `OCR_LOG_LEVEL` | `INFO` | Log level |
| `OCR_GOTENBERG_URL` | `http://localhost:3000` | Gotenberg document conversion API (LibreOffice + Chromium endpoints). Overridden to `http://gotenberg:3000` inside Docker Compose via `docker-compose.yml` environment. Required for office docs, URL, and HTML source types. |
