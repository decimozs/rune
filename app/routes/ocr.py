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
from services.converter import converter
from services.batch import batch_processor, MAX_BATCH_SIZE, DEFAULT_CONCURRENCY
from services.background import background_processor
from schemas.ocr import BatchItemResult, BatchStatus, SingleJobStatus


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


TEXT_BASED_TYPES = {
    "text/csv",
    "text/plain",
    "text/rtf",
    "text/html",
    "message/rfc822",
}


def validate_magic_bytes(file_path: Path, declared_content_type: str) -> None:
    if declared_content_type in TEXT_BASED_TYPES:
        return

    detected = magic.from_file(str(file_path), mime=True)
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

    if converter.needs_conversion(content_type):
        tmp_path = await converter.to_pdf(tmp_path, content_type)
        content_type = "application/pdf"

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


@router.post("/parse/jobs", status_code=202)
async def create_job(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
):
    validate_upload(file)

    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(413, "File too large")

    filename = cast(str, file.filename)
    content_type = cast(str, file.content_type)

    job_id = background_processor.create_job(
        filename, content_type, content, output_format.value
    )
    job = background_processor.get_job(job_id)

    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(timezone.utc),
            model=settings.version,
            format=output_format.value,
        ),
        data={
            "job_id": job_id,
            "status": job.status,
            "file_name": job.file_name,
            "file_type": job.file_type,
            "created_at": job.created_at.isoformat(),
        },
    ).model_dump(exclude_none=True)


@router.get("/parse/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = background_processor.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")

    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(timezone.utc),
            model=settings.version,
            format=job.output_format,
        ),
        data=SingleJobStatus(
            job_id=job.id,
            status=job.status,
            file_name=job.file_name,
            file_type=job.file_type,
            created_at=job.created_at,
            completed_at=job.completed_at,
            processing_time_ms=job.processing_time_ms,
            data=job.data if job.status == "completed" else None,
            error=job.error if job.status == "failed" else None,
        ).model_dump(exclude_none=True),
    ).model_dump(exclude_none=True)


@router.post("/parse/batch", status_code=202)
async def parse_batch(
    file: list[UploadFile] = File(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    concurrency: int = Query(DEFAULT_CONCURRENCY, ge=1, le=4),
):
    if len(file) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"Max {MAX_BATCH_SIZE} files per batch")
    if len(file) == 0:
        raise HTTPException(400, "At least one file required")

    files_data = [
        (cast(str, f.filename), cast(str, f.content_type), await f.read())
        for f in file
    ]
    batch_id = batch_processor.create_job(files_data, output_format.value, concurrency)
    job = batch_processor.get_job(batch_id)

    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(timezone.utc),
            model=settings.version,
            format=output_format.value,
        ),
        data={
            "batch_id": batch_id,
            "status": job.status,
            "total_files": job.total_files,
            "created_at": job.created_at.isoformat(),
        },
    ).model_dump(exclude_none=True)


@router.get("/parse/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    job = batch_processor.get_job(batch_id)
    if not job:
        raise HTTPException(404, f"Batch {batch_id} not found")

    completed = sum(1 for r in job.results if r is not None and r.success)
    failed = sum(1 for r in job.results if r is not None and not r.success)

    items = []
    for r in job.results:
        if r is None:
            items.append(None)
        else:
            items.append(
                BatchItemResult(
                    file_name=r.file_name,
                    file_type=r.file_type,
                    processing_time_ms=r.processing_time_ms,
                    success=r.success,
                    data=r.data if r.success else None,
                    error=r.error if not r.success else None,
                )
            )

    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(timezone.utc),
            model=settings.version,
            format=job.output_format,
        ),
        data=BatchStatus(
            batch_id=job.id,
            status=job.status,
            total_files=job.total_files,
            completed=completed,
            failed=failed,
            processing_time_ms=job.processing_time_ms,
            items=items,
            created_at=job.created_at,
        ),
    ).model_dump(exclude_none=True)
