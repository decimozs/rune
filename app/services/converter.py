import httpx
import logging
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

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
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    def needs_conversion(self, content_type: str) -> bool:
        return content_type in CONVERTIBLE_TYPES

    async def start(self):
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120))

    async def stop(self):
        if self._client:
            await self._client.aclose()

    async def to_pdf(self, path: Path, content_type: str) -> Path:
        pdf_path = path.with_suffix(".pdf")
        with open(path, "rb") as f:
            resp = await self._client.post(
                f"{settings.gotenberg_url}/forms/libreoffice/convert",
                files={"files": (path.name, f, content_type)},
            )
        resp.raise_for_status()
        pdf_path.write_bytes(resp.content)
        path.unlink(missing_ok=True)
        logger.info("Converted %s -> %s", path.name, pdf_path.name)
        return pdf_path


converter = DocumentConverter()
