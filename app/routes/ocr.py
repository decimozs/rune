import uuid
import time
import asyncio
import aiofiles
import magic
from pathlib import Path
from datetime import datetime, timezone
from typing import cast
from enum import Enum
from fastapi import APIRouter, File, Query, UploadFile, HTTPException
from config import settings
from schemas.response import APIResponse, ResponseMetadata
from services.ocr import ocr_service


class OutputFormat(str, Enum):
    json = "json"
    markdown = "markdown"


router = APIRouter(prefix="/ocr", tags=["ocr"])


def validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(400, "Missing filename")
    if file.content_type not in settings.allowed_types_list:
        raise HTTPException(
            415,
            f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(settings.allowed_types_list)}",
        )


def validate_magic_bytes(file_path: Path, declared_content_type: str) -> None:
    detected = magic.from_file(str(file_path), mime=True)
    # allow image/* flexibility (e.g. jpeg vs jpg variants)
    if detected != declared_content_type:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            415,
            f"File content does not match declared type. "
            f"Declared: {declared_content_type}, Detected: {detected}",
        )


async def save_upload_securely(file: UploadFile) -> Path:
    safe_name = Path(cast(str, file.filename)).name
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    tmp_path = settings.upload_dir_path / unique_name
    total = 0
    async with aiofiles.open(tmp_path, "wb") as f:
        while chunk := await file.read(8192):
            total += len(chunk)
            if total > settings.max_file_size:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(413, "File too large")
            await f.write(chunk)
    return tmp_path


def build_response(
    data,
    output_format: OutputFormat,
    filename: str,
    content_type: str,
    elapsed: float,
) -> dict:
    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(timezone.utc),
            model=settings.version,
            format=output_format.value,
            processing_time_ms=elapsed,
            file_name=filename,
            file_type=content_type,
        ),
        data=data,
    ).model_dump(exclude_none=True)


@router.post("/parse")
async def parse_file(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(default=OutputFormat.json, alias="format"),
):
    validate_upload(file)
    tmp_path = await save_upload_securely(file)

    validate_magic_bytes(tmp_path, cast(str, file.content_type))

    filename = cast(str, file.filename)
    content_type = cast(str, file.content_type)
    start = time.time()

    try:
        if output_format == OutputFormat.markdown:
            content = await asyncio.to_thread(
                ocr_service.to_markdown,
                str(tmp_path),
                filename,
                content_type,
            )
        else:
            content = await asyncio.to_thread(
                ocr_service.process,
                str(tmp_path),
                filename,
                content_type,
            )

        elapsed = round((time.time() - start) * 1000, 2)
        return build_response(content, output_format, filename, content_type, elapsed)

    finally:
        tmp_path.unlink(missing_ok=True)
