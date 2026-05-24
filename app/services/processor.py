"""Orchestration layer for file/URL/HTML OCR pipelines.

Each process_* function handles the full pipeline for one source type:
write temp file → optional Gotenberg conversion → OCR → return result.

All functions acquire _ocr_semaphore before calling PaddleOCR because
PaddleOCR is NOT thread-safe. This is the sole concurrency throttle
shared across sync, background job, and batch flows.

OCR calls are wrapped in asyncio.to_thread since PaddleOCR is synchronous
and CPU-bound. Temp files are cleaned up in finally blocks.
"""

import asyncio
import time
import uuid
import magic
import logging
from pathlib import Path
from typing import Optional

from config import settings
from services.converter import converter
from services.ocr import ocr_service
from services.url_guard import validate_url
from schemas.ocr import JsonOutputOptions

logger = logging.getLogger(__name__)

TEXT_BASED_TYPES = {
    "text/csv", "text/plain", "text/rtf", "text/html", "message/rfc822",
}

# Module-level semaphore bounds concurrent PaddleOCR calls across ALL
# callers (background jobs, batch jobs, sync requests). PaddleOCR is not
# thread-safe, so this is essential for correctness, not just performance.
_ocr_semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)


async def process_file(
    content: bytes,
    filename: str,
    declared_type: str,
    output_format: str,
    options: Optional[dict] = None,
) -> tuple[object, str | None, float]:
    """Full OCR pipeline for an uploaded file.

    Args:
        content: Raw file bytes.
        filename: Original filename (used for display, path sanitized).
        declared_type: MIME type from the upload Content-Type header.
        output_format: "json", "markdown", or "xml".
        options: JsonOutputOptions serialized as dict (only for json format).

    Returns:
        Tuple of (result_data, error_string_or_None, elapsed_ms).
    """
    async with _ocr_semaphore:
        start = time.time()

        stem = uuid.uuid4().hex
        safe_filename = Path(filename).name
        safe = settings.upload_dir_path / f"{stem}_{safe_filename}"

        try:
            safe.write_bytes(content)

            # Trust the declared type for text-based MIMEs (avoid magic overhead).
            # Otherwise detect with python-magic and reject unknown types.
            if declared_type in TEXT_BASED_TYPES:
                detected = declared_type
            else:
                detected = magic.from_file(str(safe), mime=True)
                if detected not in settings.allowed_types_list:
                    safe.unlink(missing_ok=True)
                    return None, f"Unsupported type: {detected}", round((time.time() - start) * 1000, 2)

            # Office docs need Gotenberg LibreOffice conversion before OCR
            if converter.needs_conversion(detected):
                safe = await converter.to_pdf(safe, detected)
                detected = "application/pdf"

            # Dispatch to the right OCR path based on output format.
            # All OCR calls are CPU-bound synchronous — run in thread pool.
            if output_format == "markdown":
                result = await asyncio.to_thread(
                    ocr_service.to_markdown, str(safe), filename, detected
                )
            elif output_format == "xml":
                result = await asyncio.to_thread(
                    ocr_service.to_xml, str(safe), filename, detected
                )
            else:
                opts = JsonOutputOptions(**options) if options else None
                result = await asyncio.to_thread(
                    ocr_service.process, str(safe), filename, detected, opts
                )

            elapsed = round((time.time() - start) * 1000, 2)
            return result, None, elapsed

        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            return None, f"{type(e).__name__}: {e}", elapsed

        finally:
            safe.unlink(missing_ok=True)


async def process_url(
    url_str: str,
    output_format: str,
    options: Optional[dict] = None,
) -> tuple[object, str | None, float]:
    """Full OCR pipeline for a URL source.

    Steps: validate URL (SSRF check) → Gotenberg Chromium → PDF → OCR.
    """
    async with _ocr_semaphore:
        start = time.time()
        stem = uuid.uuid4().hex
        safe = settings.upload_dir_path / f"{stem}.pdf"
        try:
            validate_url(url_str)
            safe = await converter.url_to_pdf(url_str, safe)
            display_name = f"{stem}.pdf"
            if output_format == "markdown":
                result = await asyncio.to_thread(ocr_service.to_markdown, str(safe), display_name, "application/pdf")
            elif output_format == "xml":
                result = await asyncio.to_thread(ocr_service.to_xml, str(safe), display_name, "application/pdf")
            else:
                opts = JsonOutputOptions(**options) if options else None
                result = await asyncio.to_thread(ocr_service.process, str(safe), display_name, "application/pdf", opts)
            elapsed = round((time.time() - start) * 1000, 2)
            return result, None, elapsed
        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            return None, f"{type(e).__name__}: {e}", elapsed
        finally:
            safe.unlink(missing_ok=True)


async def process_html(
    files: list[tuple[str, bytes]],
    output_format: str,
    options: Optional[dict] = None,
) -> tuple[object, str | None, float]:
    """Full OCR pipeline for HTML + assets upload.

    Steps: Gotenberg Chromium → PDF → OCR.
    """
    async with _ocr_semaphore:
        start = time.time()
        stem = uuid.uuid4().hex
        safe = settings.upload_dir_path / f"{stem}.pdf"
        try:
            files_dict = {name: content for name, content in files}
            safe = await converter.html_to_pdf(files_dict, safe)
            display_name = f"{stem}.pdf"
            if output_format == "markdown":
                result = await asyncio.to_thread(ocr_service.to_markdown, str(safe), display_name, "application/pdf")
            elif output_format == "xml":
                result = await asyncio.to_thread(ocr_service.to_xml, str(safe), display_name, "application/pdf")
            else:
                opts = JsonOutputOptions(**options) if options else None
                result = await asyncio.to_thread(ocr_service.process, str(safe), display_name, "application/pdf", opts)
            elapsed = round((time.time() - start) * 1000, 2)
            return result, None, elapsed
        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            return None, f"{type(e).__name__}: {e}", elapsed
        finally:
            safe.unlink(missing_ok=True)

