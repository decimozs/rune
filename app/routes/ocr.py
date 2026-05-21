import uuid
import time
import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, File, Query, UploadFile, HTTPException

from config import settings
from schemas.response import APIResponse, ResponseMetadata
from services.ocr import ocr_service
from enum import Enum


class OutputFormat(str, Enum):
    json = "json"
    markdown = "markdown"


router = APIRouter(prefix="/ocr", tags=["ocr"])


def validate_upload(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, "Missing filename")

    if file.content_type not in settings.allowed_types_list:
        raise HTTPException(
            415,
            f"Unsupported file type: {file.content_type}. Allowed: {', '.join(settings.allowed_types_list)}",
        )


async def save_upload_securely(file: UploadFile) -> Path:
    safe_name = Path(file.filename).name
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
    file: UploadFile,
    elapsed: float,
) -> dict:
    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(timezone.utc),
            model="PP-OCRv4",
            format=output_format.value,
            processing_time_ms=elapsed,
            file_name=file.filename,
            file_type=file.content_type,
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
    start = time.time()

    try:
        if output_format == OutputFormat.markdown:
            content = await asyncio.to_thread(
                ocr_service.to_markdown, str(tmp_path), file
            )
        else:
            content = await asyncio.to_thread(ocr_service.process, str(tmp_path), file)

        elapsed = round((time.time() - start) * 1000, 2)
        return build_response(content, output_format, file, elapsed)

    finally:
        if tmp_path.exists():
            tmp_path.unlink()
