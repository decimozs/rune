import asyncio
import time
import uuid
import magic
import logging
from pathlib import Path

from config import settings
from services.converter import converter
from services.ocr import ocr_service

logger = logging.getLogger(__name__)

TEXT_BASED_TYPES = {
    "text/csv", "text/plain", "text/rtf", "text/html", "message/rfc822",
}

# Shared semaphore bounds concurrent OCR calls across background + batch processors.
# PaddleOCR is not thread-safe; this prevents CPU/memory overload under parallel load.
_ocr_semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)

async def process_file(
    content: bytes,
    filename: str,
    declared_type: str,
    output_format: str,
) -> tuple[object, str | None, float]:
    async with _ocr_semaphore:
        start = time.time()

        stem = uuid.uuid4().hex
        safe_filename = Path(filename).name
        safe = settings.upload_dir_path / f"{stem}_{safe_filename}"

        try:
            safe.write_bytes(content)

            if declared_type in TEXT_BASED_TYPES:
                detected = declared_type
            else:
                detected = magic.from_file(str(safe), mime=True)
                if detected not in settings.allowed_types_list:
                    safe.unlink(missing_ok=True)
                    return None, f"Unsupported type: {detected}", round((time.time() - start) * 1000, 2)

            if converter.needs_conversion(detected):
                safe = await converter.to_pdf(safe, detected)
                detected = "application/pdf"

            if output_format == "markdown":
                result = await asyncio.to_thread(
                    ocr_service.to_markdown, str(safe), filename, detected
                )
            elif output_format == "xml":
                result = await asyncio.to_thread(
                    ocr_service.to_xml, str(safe), filename, detected
                )
            else:
                result = await asyncio.to_thread(
                    ocr_service.process, str(safe), filename, detected
                )

            elapsed = round((time.time() - start) * 1000, 2)
            return result, None, elapsed

        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            return None, f"{type(e).__name__}: {e}", elapsed

        finally:
            safe.unlink(missing_ok=True)
