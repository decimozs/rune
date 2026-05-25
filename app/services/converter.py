"""Gotenberg client for document-to-PDF conversion.

Three conversion modes:
    - LibreOffice: Office docs (DOC, DOCX, PPT, XLS, etc.)
    - Chromium URL:  Fetch a web page URL and render to PDF
    - Chromium HTML: Upload HTML file + assets and render to PDF

Gotenberg must be running separately. Timeout is 120s for all
conversions. The httpx client is a singleton managed in main.py
lifespan (start/stop).
"""

import logging
from pathlib import Path

import httpx
from config import settings

logger = logging.getLogger(__name__)

# MIME types that get routed through Gotenberg LibreOffice for PDF conversion.
# Images and PDFs are OCR'd directly without conversion.
CONVERTIBLE_TYPES = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/rtf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class DocumentConverter:
    """HTTP client wrapper for Gotenberg conversion API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def needs_conversion(self, content_type: str) -> bool:
        """Return True if this MIME type requires LibreOffice conversion."""
        return content_type in CONVERTIBLE_TYPES

    async def start(self) -> None:
        """Create the shared httpx client. Called in lifespan startup."""
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120))

    async def stop(self) -> None:
        """Close the shared httpx client. Called in lifespan shutdown."""
        if self._client:
            await self._client.aclose()

    async def to_pdf(self, path: Path, content_type: str) -> Path:
        """Convert an office document to PDF via Gotenberg LibreOffice.

        The original file is deleted after successful conversion.
        The returned Path points to the new .pdf file.
        """
        pdf_path = path.with_suffix(".pdf")
        with open(path, "rb") as f:
            resp = await self._client.post(
                f"{settings.gotenberg_url}/forms/libreoffice/convert",
                files={"files": (path.name, f, content_type)},
            )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error("Gotenberg %s %s: %s", resp.status_code, resp.url, resp.text)
            raise
        pdf_path.write_bytes(resp.content)
        path.unlink(missing_ok=True)
        logger.info("Converted %s -> %s", path.name, pdf_path.name)
        return pdf_path

    async def url_to_pdf(self, url: str, output_path: Path) -> Path:
        """Fetch a URL via Gotenberg Chromium and save as PDF.

        Sends empty files dict to force multipart/form-data encoding,
        which Gotenberg requires for the URL endpoint.
        """
        resp = await self._client.post(
            f"{settings.gotenberg_url}/forms/chromium/convert/url",
            data={"url": url},
            files={"": ""},
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error("Gotenberg %s %s: %s", resp.status_code, resp.url, resp.text)
            raise
        output_path.write_bytes(resp.content)
        logger.info("URL -> %s", output_path.name)
        return output_path

    async def html_to_pdf(self, files: dict[str, bytes], output_path: Path) -> Path:
        """Convert HTML + assets to PDF via Gotenberg Chromium.

        Gotenberg requires:
            - The main HTML file sent as field ``index.html``
            - All assets (CSS, JS, images) sent as field ``files``
            - Any .html/.htm file is renamed to index.html in the
              Content-Disposition filename.
        """
        req = []
        for name, content in files.items():
            if name.endswith((".html", ".htm")):
                field = "index.html"
                mime = "text/html"
                send_name = "index.html"
            else:
                field = "files"
                mime = "application/octet-stream"
                send_name = name
            req.append((field, (send_name, content, mime)))
        resp = await self._client.post(
            f"{settings.gotenberg_url}/forms/chromium/convert/html",
            files=req,
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error("Gotenberg %s %s: %s", resp.status_code, resp.url, resp.text)
            raise
        output_path.write_bytes(resp.content)
        logger.info("HTML -> %s", output_path.name)
        return output_path


converter = DocumentConverter()
