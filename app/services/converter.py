import logging
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

CONVERTIBLE_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/rtf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class DocumentConverter:
    def needs_conversion(self, content_type: str) -> bool:
        return content_type in CONVERTIBLE_TYPES

    async def to_pdf(self, path: Path, content_type: str) -> Path:
        import httpx

        pdf_path = path.with_suffix(".pdf")
        async with httpx.AsyncClient() as client:
            with open(path, "rb") as f:
                resp = await client.post(
                    f"{settings.gotenberg_url}/forms/libreoffice/convert",
                    files={"files": (path.name, f, content_type)},
                    timeout=120,
                )
            resp.raise_for_status()
            pdf_path.write_bytes(resp.content)
        path.unlink(missing_ok=True)
        logger.info("Converted %s -> %s", path.name, pdf_path.name)
        return pdf_path


converter = DocumentConverter()
