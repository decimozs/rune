# Getting Started

This guide walks you through your first OCR request. You do not need to be a developer to follow along — but you will need access to the server URL and an API key from your team's technical contact.

## What You Need

- **Server URL** — the address where the OCR service is running (e.g., `http://ocr.company.com` or `http://localhost:8000` for local testing)
- **API key** — a secret key that identifies you to the system. Get this from your team's admin or DevOps contact
- **A file** — an image, PDF, or office document you want to extract text from

## Option 1: Command Line (curl)

If you have access to a terminal, you can use `curl` — a tool built into macOS and Linux, and available for Windows.

### Basic Request

```bash
curl -X POST http://localhost:8000/ocr/parse \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@/path/to/your/document.pdf"
```

Replace:
- `http://localhost:8000` with your server URL
- `your-api-key-here` with your actual API key
- `/path/to/your/document.pdf` with the path to your file

### Get Markdown Instead of JSON

```bash
curl -X POST "http://localhost:8000/ocr/parse?format=markdown" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@/path/to/your/document.docx"
```

### Get Page Images With the Text

If you want both the text AND pictures of each page with detected text regions highlighted, use JSON format (the default) and include `page_image_url` in the response. You can open that URL in your browser to see the image.

```bash
curl -X POST http://localhost:8000/ocr/parse \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@/path/to/your/document.pdf"
```

Look for the `page_image_url` field in the response — it will look like `http://your-nginx-server:8080/assets/pages/abc123/page_1.png`.

## Option 2: From Your Own Application

You can call the OCR API from any programming language. Here are examples:

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/ocr/parse",
    headers={"X-API-Key": "your-api-key-here"},
    files={"file": open("document.pdf", "rb")}
)

result = response.json()
if result["success"]:
    for page in result["data"]["pages"]:
        print(f"Page {page['page']}:")
        for word in page["words"]:
            print(f"  - {word['text']}")
```

### JavaScript (in Node.js)

```javascript
const fs = require("fs");
const FormData = require("form-data");
const axios = require("axios");

const form = new FormData();
form.append("file", fs.createReadStream("document.pdf"));

const response = await axios.post(
  "http://localhost:8000/ocr/parse",
  form,
  {
    headers: {
      ...form.getHeaders(),
      "X-API-Key": "your-api-key-here",
    },
  }
);

console.log(response.data);
```

## What Happens Next?

The server processes your file and returns the extracted text. Depending on the file size and server load, this takes anywhere from a few seconds (for a small image) to a minute or more (for a long PDF or complex office document).

If you used the "background job" or "batch" mode, the server returns immediately with a job ID. You can check back later for the result.

## Common Issues

| Problem | Likely Reason | What To Do |
|---|---|---|
| "Missing API key" | You did not include the key | Add `-H "X-API-Key: your-key"` to your request |
| "Invalid API key" | The key is wrong or expired | Ask your admin for a new key |
| "Unsupported file type" | The file format is not accepted | Convert to PDF or PNG first |
| "File too large" | The file exceeds the 50MB limit | Split the file into smaller parts |
| Connection refused | The server is not running | Check with your DevOps team |
