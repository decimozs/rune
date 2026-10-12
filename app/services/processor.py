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
import logging
import time
import uuid
from pathlib import Path

import magic
from config import settings
from schemas.ocr import JsonOutputOptions
from services.converter import converter
from services.exceptions import OCRValidationError
from services.log_ctx import sanitize_url
from services.ocr import ocr_service
from services.url_guard import validate_url

logger = logging.getLogger(__name__)

TEXT_BASED_TYPES = {
    "text/csv",
    "text/plain",
    "text/rtf",
    "text/html",
    "message/rfc822",
}

# Module-level semaphore bounds concurrent PaddleOCR calls across ALL
# callers (background jobs, batch jobs, sync requests). PaddleOCR is not
# thread-safe, so this is essential for correctness, not just performance.
_ocr_semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)


async def _run_ocr(
    safe_path: Path,
    display_name: str,
    detected_type: str,
    output_format: str,
    options: dict | None = None,
    version: str | None = None,
):
    """Dispatch to the right OCR backend by output format. Shared by all source types."""
    if output_format == "markdown":
        return await asyncio.to_thread(
            ocr_service.to_markdown,
            str(safe_path),
            display_name,
            detected_type,
            version,
        )
    elif output_format == "xml":
        return await asyncio.to_thread(
            ocr_service.to_xml, str(safe_path), display_name, detected_type, version
        )
    opts = JsonOutputOptions(**options) if options else None
    return await asyncio.to_thread(
        ocr_service.process, str(safe_path), display_name, detected_type, opts, version
    )


async def process_file(
    content: bytes | Path,
    filename: str,
    declared_type: str,
    output_format: str,
    options: dict | None = None,
    version: str | None = None,
) -> tuple[object, str | None, float]:
    """Full OCR pipeline for an uploaded file.

    Args:
        content: Raw file bytes OR an existing Path to a temp file
                 already on disk (avoids double-buffering in memory).
        filename: Original filename (used for display, path sanitized).
        declared_type: MIME type from the upload Content-Type header.
        output_format: "json", "markdown", or "xml".
        options: JsonOutputOptions serialized as dict (only for json format).
        version: Model version override (e.g. "PP-OCRv5").

    Returns:
        Tuple of (result_data, error_string_or_None, elapsed_ms).
    """
    async with _ocr_semaphore:
        start = time.time()
        content_size = (
            len(content) if isinstance(content, bytes) else Path(content).stat().st_size
        )
        logger.info(
            "Processing file: name=%s, type=%s, size=%d, format=%s",
            filename,
            declared_type,
            content_size,
            output_format,
        )

        if isinstance(content, Path):
            safe = content
            stem = safe.stem
        else:
            stem = uuid.uuid4().hex
            safe_filename = Path(filename).name
            safe = settings.upload_dir_path / f"{stem}_{safe_filename}"
            safe.write_bytes(content)

        try:
            if declared_type in TEXT_BASED_TYPES:
                detected = declared_type
            else:
                detected = magic.from_file(str(safe), mime=True)
                if detected not in settings.allowed_types_list:
                    safe.unlink(missing_ok=True)
                    logger.warning(
                        "Unsupported type: name=%s, detected=%s", filename, detected
                    )
                    return (
                        None,
                        f"Unsupported type: {detected}",
                        round((time.time() - start) * 1000, 2),
                    )

            if converter.needs_conversion(detected):
                logger.info(
                    "Converting via Gotenberg: name=%s, type=%s", filename, detected
                )
                safe = await converter.to_pdf(safe, detected)
                detected = "application/pdf"

            result = await _run_ocr(
                safe, filename, detected, output_format, options, version
            )

            elapsed = round((time.time() - start) * 1000, 2)
            logger.info(
                "Processing complete: name=%s, format=%s, duration=%sms",
                filename,
                output_format,
                elapsed,
            )
            return result, None, elapsed

        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            logger.error(
                "Processing failed: name=%s, error=%s, duration=%sms",
                filename,
                e,
                elapsed,
            )
            return None, "Processing failed", elapsed

        finally:
            safe.unlink(missing_ok=True)


async def process_url(
    url_str: str,
    output_format: str,
    options: dict | None = None,
    version: str | None = None,
) -> tuple[object, str | None, float]:
    """Full OCR pipeline for a URL source.

    Steps: validate URL (SSRF check) → Gotenberg Chromium → PDF → OCR.
    """
    async with _ocr_semaphore:
        start = time.time()
        logger.info(
            "Processing URL: url=%s, format=%s", sanitize_url(url_str), output_format
        )
        stem = uuid.uuid4().hex
        safe = settings.upload_dir_path / f"{stem}.pdf"
        try:
            validate_url(url_str)
            safe = await converter.url_to_pdf(url_str, safe)
            display_name = f"{stem}.pdf"
            result = await _run_ocr(
                safe, display_name, "application/pdf", output_format, options, version
            )
            elapsed = round((time.time() - start) * 1000, 2)
            logger.info("URL processing complete: duration=%sms", elapsed)
            return result, None, elapsed
        except OCRValidationError as e:
            elapsed = round((time.time() - start) * 1000, 2)
            logger.warning("URL validation failed: error=%s, duration=%sms", e, elapsed)
            return None, str(e), elapsed
        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            logger.error("URL processing failed: error=%s, duration=%sms", e, elapsed)
            return None, "Processing failed", elapsed
        finally:
            safe.unlink(missing_ok=True)


async def process_html(
    files: list[tuple[str, bytes]],
    output_format: str,
    options: dict | None = None,
    version: str | None = None,
) -> tuple[object, str | None, float]:
    """Full OCR pipeline for HTML + assets upload.

    Steps: Gotenberg Chromium → PDF → OCR.
    """
    async with _ocr_semaphore:
        start = time.time()
        logger.info("Processing HTML: files=%d, format=%s", len(files), output_format)
        stem = uuid.uuid4().hex
        safe = settings.upload_dir_path / f"{stem}.pdf"
        try:
            files_dict = dict(files)
            safe = await converter.html_to_pdf(files_dict, safe)
            display_name = f"{stem}.pdf"
            result = await _run_ocr(
                safe, display_name, "application/pdf", output_format, options, version
            )
            elapsed = round((time.time() - start) * 1000, 2)
            logger.info(
                "HTML processing complete: files=%d, duration=%sms", len(files), elapsed
            )
            return result, None, elapsed
        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            logger.error("HTML processing failed: error=%s, duration=%sms", e, elapsed)
            return None, "Processing failed", elapsed
        finally:
            safe.unlink(missing_ok=True)
