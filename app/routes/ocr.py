import shutil
import time
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, File, Query, UploadFile

from schemas.response import APIResponse, ResponseMetadata
from services.ocr import ocr_service
from enum import Enum


class OutputFormat(str, Enum):
    json = "json"
    markdown = "markdown"


router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/parse")
async def parse_file(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(default=OutputFormat.json, alias="format"),
):
    tmp_path = Path(f"/tmp/{file.filename}")
    start = time.time()

    try:
        with tmp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if output_format == OutputFormat.markdown:
            content = ocr_service.to_markdown(str(tmp_path), file)
            elapsed = round((time.time() - start) * 1000, 2)
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
                data=content,
            ).model_dump(exclude_none=True)

        result = ocr_service.process(str(tmp_path), file)
        elapsed = round((time.time() - start) * 1000, 2)
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
            data=result,
        ).model_dump(exclude_none=True)

    finally:
        if tmp_path.exists():
            tmp_path.unlink()
