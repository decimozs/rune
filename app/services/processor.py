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


async def process_file(
    content: bytes,
    filename: str,
    declared_type: str,
    output_format: str,
) -> tuple[object, str | None, float]:
    start = time.time()

    safe = Path(settings.upload_dir) / f"{uuid.uuid4().hex}_{filename}"

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
