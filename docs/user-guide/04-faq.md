# Frequently Asked Questions

## General

### What does OCR stand for?

OCR stands for Optical Character Recognition. It is the technology that reads text from images. If you have ever used a scanner that turned a paper document into editable text, you have used OCR.

### Does this work like Google Drive's OCR?

Yes. Google Drive can extract text from uploaded PDFs and images — this does the same thing. The main difference is that Google sends your files to their cloud servers. This tool runs on your own infrastructure, so your documents stay private.

### Why not just use Google or Adobe?

| Reason | Explanation |
|---|---|
| **Privacy** | Your documents never leave your network. No third-party cloud service sees your data |
| **Cost** | No per-page or per-document fees. You pay for the server once, not per file |
| **Control** | You decide when to update, how to configure, and which files to process |
| **Offline** | Works without internet access |

### How accurate is it?

On clear, well-scanned documents, accuracy is typically 95-99%. Accuracy depends on image quality, language, and document complexity. For reference, cloud OCR services (Google Cloud Vision, AWS Textract) report similar accuracy ranges.

## Usage

### What files can I upload?

Images (PNG, JPG, BMP, TIFF, WebP), PDFs, and office documents (Word, Excel, PowerPoint, RTF, CSV). If your file type is not listed, try converting it to PDF first.

### How large can my files be?

Up to 50MB by default. Your technical team can increase this limit if needed.

### How long does it take?

Depends on file size and server load:
- A small image (100KB): 1-5 seconds
- A 10-page PDF: 10-30 seconds
- A 50-page office document: 30-90 seconds

### Can I process multiple files at once?

Yes. Use the **batch** endpoint to submit up to 20 files at the same time. Each file is processed independently — if one fails, the others still complete.

### Can I process web pages?

Yes. Use the URL source type. The system visits the web page, converts it to PDF, and extracts the text. Note that complex web applications with lots of JavaScript may not render fully.

### How long are my results kept?

- **Page images** are automatically deleted after 1 hour
- **Background and batch job results** expire after 1 hour
- **Uploaded files** are deleted immediately after processing

This is designed for security — no data is permanently stored.

## Troubleshooting

### Why did I get a confidence score below 0.50?

Low confidence usually means the image quality was poor, the text was very small, or the font was unusual. Try:
- Using a higher resolution image
- Ensuring good lighting (no shadows on the text)
- Straightening the image if it was taken at an angle
- Checking that the text is printed (handwriting has lower accuracy)

### Why is some text missing or wrong?

OCR is not perfect. Common issues include:
- Very small or decorative fonts
- Text overlaid on images or colored backgrounds
- Watermarks or stamps
- Dense tables with many columns
- Text at extreme angles

If accuracy is important, compare the output against the page images.

### The server is not responding

Contact your technical team or DevOps contact. They can check:
- Is the server running?
- Is the URL correct?
- Are the Ports (8000, 8080) accessible?

### I got a 413 error

The file is too large. The default limit is 50MB. Try:
- Compressing the file
- Splitting it into smaller parts
- Asking your admin to increase the limit

### How do I get an API key?

Contact your team's technical admin or DevOps contact. They can generate a key using the key management tools.

## Technical Questions

### Is this open source?

The core OCR engine (PaddleOCR) and document converter (Gotenberg) are open source. The application code that connects them is also open source within the company.

### Can I integrate this with my application?

Yes. The API follows standard REST conventions. Call the OCR endpoints from any programming language that can make HTTP requests (Python, JavaScript, Java, C#, etc.).

### Can I run this on my laptop?

Yes. See the [Quick Start](../tech/02-quickstart.md) guide for local setup instructions. You will need Docker installed.

### Does it work on Windows / macOS / Linux?

The Docker setup works on all three. For running without Docker, Linux is recommended — the system dependencies are easiest to install on Ubuntu/Debian. macOS works with Homebrew. Windows requires additional setup (see [Prerequisites](../tech/06-prerequisites.md)).
