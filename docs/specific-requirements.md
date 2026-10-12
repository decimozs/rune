# Specific Requirements

## Overview

Rune is a self-hosted OCR service using PaddleOCR (PP-OCRv4). It accepts images, PDFs, office documents, URLs, and HTML — returns extracted text as JSON, Markdown, or XML.

## Software Requirements

### Docker (Recommended)

| Component | Version | Notes |
|---|---|---|
| Docker Engine | 24+ | Required for docker-compose deployment |
| Docker Compose | v2 | Included with Docker Desktop / modern Engine |

### Python (Local Development Only)

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| uv | Latest (pip install alternative) |

### System Libraries (Local Dev Only)

| Library | Purpose |
|---|---|
| libmagic1 | MIME type detection |
| libgl1 | OpenCV image processing |
| libglib2.0-0 | OpenCV data structures |
| libsm6, libxext6, libxrender1 | X11 display (OpenCV) |
| libgomp1 | OpenMP (PaddlePaddle parallel) |
| libstdc++6 | C++ stdlib (PaddlePaddle) |
| poppler-utils | PDF rendering (pdftoppm) |

### Required Services

| Service | Purpose | Required For |
|---|---|---|
| Gotenberg (port 3000) | Convert office docs, URLs, HTML to PDF | DOC/DOCX/XLSX/PPTX/RTF/CSV/URL/HTML sources |
| nginx (port 8080) | Serve page images from OCR output | page_image_url in API responses |
| OCR API (port 8000) | The application itself | Everything |

Images and native PDFs work without Gotenberg.

## Hardware Requirements

### Minimum (Single User, Occasional)

| Resource | Requirement |
|---|---|
| CPU | 2 cores (x86_64) |
| RAM | 4 GB |
| Disk | 10 GB free |
| Network | LAN, any |

### Recommended (Production / Multi-User)

| Resource | Requirement |
|---|---|
| CPU | 4+ cores (x86_64 or arm64) |
| RAM | 8 GB |
| Disk | 20 GB+ (Premium SSD) |
| Network | Low latency between API and Gotenberg |

### Azure VM Sizing (Reference)

| SKU | vCPU | RAM | Disk | Use Case |
|---|---|---|---|---|
| Standard D2s v3 | 2 | 8 GB | Premium SSD | Light usage |
| Standard D4s v3 | 4 | 16 GB | Premium SSD | Moderate usage |

### GPU

Not required. PaddlePaddle wheels used are CPU-only. GPU support requires switching to `paddlepaddle-gpu` package and mounting CUDA runtime.

## Model Requirements

### Supported Models

| Model | Purpose | Default | Per-Model RAM | Per-Model Disk |
|---|---|---|---|---|
| PP-OCRv3 | Text detection + recognition (legacy) | No | ~300 MB | ~500 MB |
| PP-OCRv4 | Text detection + recognition (current default) | Yes | ~300 MB | ~500 MB |
| PP-OCRv5 | Text detection + recognition (newest) | No | ~300 MB | ~500 MB |
| PPStructureV3 | Table/layout recognition (markdown output) | Always loaded | ~150-200 MB | ~200-300 MB |

### Memory by Configuration

| Config | Models Loaded | Idle RAM | Peak RAM (2 jobs) |
|---|---|---|---|
| Default (PP-OCRv4 only) | 1 OCR + PPStructureV3 | ~500 MB | ~1.5 GB |
| Pre-load v4 + v5 | 2 OCR + PPStructureV3 | ~800 MB | ~2 GB |
| Pre-load v3 + v4 + v5 | 3 OCR + PPStructureV3 | ~1.1 GB | ~2.5 GB |

### Model Download

- **Source**: PaddlePaddle CDN (Baidu cloud)
- **Cache location**: `~/.paddleocr/` (container: `/home/appuser/.paddleocr/`)
- **Download trigger**: First call to OCR engine at startup
- **Cache persistence**: Docker volume `paddle_models` (survives container restarts)
- **Download time**: ~30-60s per model version on first run

## Disk Space Breakdown

### Docker Images

| Image | Size |
|---|---|
| rune (built API image) | **4.53 GB** |
| gotenberg/gotenberg:8 | 2.41 GB |
| nginx:alpine | 93.6 MB |

### Docker Volumes

| Volume | Contents | Typical Size |
|---|---|---|
| paddle_models | PaddleOCR model cache (~/.paddleocr/) | 500 MB - 1.2 GB |
| ocr_data | SQLite API key database | < 1 MB |
| ocr_assets | Output files (page images, markdown) | Ephemeral (1hr TTL) |

### Python Virtual Environment (Local Dev Only)

| Component | Size |
|---|---|
| paddlepaddle 3.3.1 (+ deps) | ~717 MB |
| Full .venv | ~1.6 GB |

### Cache & Temp Files

| Path | Contents | Size |
|---|---|---|
| `~/.paddleocr/` (1 version) | Downloaded model files | ~500-600 MB |
| `~/.paddleocr/` (2 versions) | v4 + v5 models | ~1-1.2 GB |

## Network Requirements

### Ports

| Port | Service | Purpose |
|---|---|---|
| 8000 | OCR API | API requests (docker maps 8000->80) |
| 8080 | nginx | Page images |
| 3000 | Gotenberg | Document conversion (internal only) |

### External Connectivity

| Destination | Purpose | Required |
|---|---|---|
| PaddlePaddle CDN | Model download on first run | Yes (first startup only) |
| pip/uv index | Dependency install | Only during image build |

## Performance Characteristics

### Startup

| Phase | Duration | Notes |
|---|---|---|
| Container start | 1-2s | Docker layer mount |
| Model download (first run) | 30-60s | Download ~500 MB from CDN |
| Model load (subsequent runs) | 22-30s | From cached volume |
| Full readiness | 30-90s | First time longer |

### Processing

| Operation | Duration | Notes |
|---|---|---|
| OCR per image (batch of 8) | ~220 ms/image | Concurrent jobs share resources |
| OCR per image (single) | ~340 ms/image | |
| Gotenberg HTML→PDF | ~432 ms average | |
| OCR init (benchmarked) | 2.1 s | After model is loaded |

### Concurrency Limits

| Setting | Default | Max | Purpose |
|---|---|---|---|
| `OCR_MAX_CONCURRENT_JOBS` | 2 | Configurable | Bounds simultaneous PaddleOCR calls |
| Uvicorn workers | 1 | 1 (Docker) | One worker per container |
| Max batch size | 20 | 20 files | Per batch endpoint call |
| Max file size | 50 MB | Configurable | Per uploaded file |

PaddleOCR is NOT thread-safe. `asyncio.to_thread()` is used to run OCR calls in a thread pool, guarded by a semaphore.

## Supported Platforms

| Platform | Docker | Local Dev | Notes |
|---|---|---|---|
| Linux (x86_64) | Full | Full | Primary target |
| macOS (Intel) | Full | Full | Gotenberg in Docker |
| macOS (Apple Silicon) | Full (arm64) | Full | PaddlePaddle arm64 wheels available |
| Windows (WSL2) | Full | Partial (libmagic) | System libs via WSL2 |
| Windows (native) | Docker Desktop | Partial | python-magic-bin required |

## Environment Variables Quick Reference

See [Configuration](tech/04-configuration.md) for full reference.

| Variable | Default | Critical? |
|---|---|---|
| OCR_API_KEYS | `#` (disabled) | Yes — set for production |
| OCR_VERSION | `PP-OCRv4` | No — change to select model |
| OCR_MODELS | `PP-OCRv4` | Yes — affects startup RAM |
| OCR_LANG | `en` | No — change for other languages |
| OCR_MAX_CONCURRENT_JOBS | `2` | Yes — affects memory usage |
| OCR_GOTENBERG_URL | `http://localhost:3000` | Yes — must point to Gotenberg |
| OCR_ASSET_BASE_URL | (empty) | Yes — set to `http://localhost:8080` for Docker |

## Key Architectural Constraints

1. **One model per version, lazy-loaded** — each unique `OCR_VERSION` value loads separately; they do not share weights
2. **PPStructureV3 always loaded** — required for markdown output; cannot be disabled separately
3. **Single-process concurrency** — uvicorn worker=1 + asyncio.Semaphore(2) means at most 2 simultaneous OCR calls in one container
4. **Model cache is long-lived** — `paddle_models` Docker volume persists across restarts; clearing it triggers fresh download
5. **Output files auto-expire** — default 1-hour TTL, swept every 5 minutes
