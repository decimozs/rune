# Prerequisites

## System Libraries

PaddleOCR and OpenCV need native system libraries to run. These are automatically included in the Docker image — only install manually if running outside Docker.

| Library | What It Is Used For |
|---|---|
| `libmagic1` | Identifies file types (detects if a file is really a PNG, not just named like one) |
| `libgl1` | OpenGL graphics — needed by OpenCV for image processing |
| `libglib2.0-0` | System data structures — OpenCV dependency |
| `libsm6`, `libxext6`, `libxrender1` | X11 display libraries — OpenCV dependency |
| `libgomp1` | Parallel processing — used by PaddlePaddle |
| `libstdc++6` | C++ standard library — PaddlePaddle and PaddleOCR need this |
| `poppler-utils` | Provides `pdftoppm` — used by PaddleOCR internally to render PDF pages to images |

### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install -y \
  libmagic1 libgl1 libglib2.0-0 libsm6 libxext6 \
  libxrender1 libgomp1 libstdc++6 libc6 curl poppler-utils
```

### macOS

```bash
brew install libmagic poppler
```

OpenCV GUI libraries are not needed on macOS.

### Windows

OpenCV GUI libraries are Linux-only. Poppler can be installed via Chocolatey:

```powershell
choco install poppler
```

Also install the Windows-specific Python package for file type detection:

```powershell
uv pip install python-magic-bin
```

## Python

Requires Python 3.11 or newer.

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all project dependencies
uv sync
```

## Docker

For running with Docker Compose, you need:

- Docker Engine 24+
- Docker Compose v2 (included with Docker Desktop)

## Gotenberg

Gotenberg converts office documents to PDF. It is required for:

- Word (DOC, DOCX), Excel (XLS, XLSX), PowerPoint (PPT, PPTX)
- Rich Text Format (RTF), CSV
- URL and HTML source types

Images and PDFs work without Gotenberg.

```bash
docker run -d --rm -p 3000:3000 --name gotenberg gotenberg/gotenberg:8
```

Verify it is running:

```bash
curl http://localhost:3000/health
```

## Verify Everything Is Set Up

```bash
# Check Python and uv
python3 --version
uv --version

# Check system libraries
ldconfig -p | grep -E "lib(magic|glib|gomp|stdc\+\+|c)-"

# Check Gotenberg (if running)
curl -sf http://localhost:3000/health && echo "Gotenberg ready" || echo "Gotenberg not running"
```
