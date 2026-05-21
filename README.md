# Exist OCR Service

Internal OCR service for **Exist Software Labs**. Uses [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (PP-OCRv4) to extract text and bounding boxes from uploaded images/documents.

> **Status: Heavy Development & Testing** — API, architecture, and features are subject to change.

## Tech Stack

- **Python** 3.11+
- **FastAPI** — web framework
- **PaddleOCR** — OCR engine (PP-OCRv4)
- **uv** — package & project management
- **Docker** — containerized deployment

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

### Run Locally

```bash
# Install dependencies
uv sync

# Start the server
uv run fastapi run app/main.py --port 8000
```

Server runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Run with Docker

```bash
docker build -t exist-ocr .
docker run -p 8000:80 exist-ocr
```

## API

### `POST /ocr/parse`

Extract text from an uploaded image file.

**Request:** `multipart/form-data` with field `file`

**cURL:**

```bash
curl -X POST http://localhost:8000/ocr/parse \
  -F "file=@path/to/image.png"
```

**Response:**

```json
{
  "file": "image.png",
  "path": "/tmp/image.png",
  "type": "image/png",
  "pages": [
    {
      "page": 1,
      "words": [
        {
          "text": "Hello World",
          "confidence": 0.9876,
          "bbox": [[10, 20], [100, 20], [100, 40], [10, 40]]
        }
      ],
      "extracted_text": "Hello World"
    }
  ]
}
```

## Project Structure

```
app/
├── main.py              # FastAPI app entrypoint
├── routes/
│   └── ocr.py           # OCR endpoint handlers
├── services/
│   └── ocr.py           # PaddleOCR wrapper
└── schemas/
    └── ocr.py           # Pydantic response models
```
