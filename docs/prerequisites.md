# Prerequisites

## System Dependencies

PaddleOCR and OpenCV require native libraries. The table below lists each dependency and its purpose:

| Package | Purpose |
|---------|---------|
| `libmagic1` | MIME type detection via `python-magic` |
| `libgl1` | OpenGL — required by OpenCV for image rendering |
| `libglib2.0-0` | GLib data structures — OpenCV dependency |
| `libsm6` | X11 Session Management — OpenCV dependency |
| `libxext6` | X11 extensions — OpenCV dependency |
| `libxrender1` | X11 rendering — OpenCV dependency |
| `libgomp1` | OpenMP parallelization — used by PaddlePaddle |
| `libstdc++6` | C++ standard library — PaddlePaddle runtime |
| `libc6` | GNU C library — base system runtime |
| `poppler-utils` | `pdftoppm` — PaddleOCR uses this internally for PDF page rendering |

### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install -y \
  libmagic1 libgl1 libglib2.0-0 libsm6 libxext6 \
  libxrender1 libgomp1 libstdc++6 libc6 curl poppler-utils
```

### macOS (Homebrew)

```bash
brew install libmagic poppler
# OpenCV GUI libs are not needed on macOS (native GUI not used)
```

### Windows

OpenCV GUI libs (`libgl1`, `libsm6`, `libxext6`, `libxrender1`) are Linux-only — not needed on Windows.

```powershell
# Install uv (if not already)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install poppler (for pdftoppm — PaddleOCR PDF rendering)
# Option A: via Chocolatey
choco install poppler
# Option B: download from https://github.com/oschwartz10612/poppler-windows/releases
#           then add bin/ folder to PATH

# Install Python deps
uv sync

# python-magic needs platform-specific DLL on Windows
uv pip install python-magic-bin

# Start Gotenberg (Docker Desktop required)
docker run -d --rm -p 3000:3000 --name gotenberg gotenberg/gotenberg:8

# Start dev server
uv run fastapi dev app/main.py --port 8000
```

### Docker (no system install needed)

If running via `docker compose up`, all system dependencies are bundled in the image — skip system install.

---

## Python Environment

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv sync
```

---

## Gotenberg (for Office Documents)

OCR service uses [Gotenberg](https://gotenberg.dev) to convert office documents (DOCX, PPT, XLSX, RTF, CSV, XLS, DOC) to PDF before OCR.

```bash
docker run -d --rm -p 3000:3000 --name gotenberg gotenberg/gotenberg:8
```

Verify it is running:

```bash
curl http://localhost:3000/health
```

If you do not need office document support, Gotenberg is optional — image and PDF OCR work without it.

---

## Verify Setup

```bash
# Check uv
uv --version

# Check Python
python3 --version

# Check system libs
ldconfig -p | grep -E "lib(magic|glib|gomp|stdc\+\+|c)-" || echo "Some libs may be missing"

# Check Gotenberg (optional)
curl -sf http://localhost:3000/health && echo "Gotenberg OK" || echo "Gotenberg not running"
```

---

## Troubleshooting

| Problem | Likely Fix |
|---------|-----------|
| `ImportError: libGL.so.1` | Install `libgl1` |
| `ImportError: libmagic.so.1` | Install `libmagic1` |
| `OSError: pdftoppm not found` | Install `poppler-utils` |
| `paddleOCR not found` | Run `uv sync` |
| Gotenberg connection refused | Start Gotenberg: `docker run --rm -p 3000:3000 gotenberg/gotenberg:8` |
| `ImportError: magic` on Windows | Run `uv pip install python-magic-bin` |
