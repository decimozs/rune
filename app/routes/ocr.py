from datetime import datetime, timezone
from typing import cast
from enum import Enum
from fastapi import APIRouter, File, Query, UploadFile, HTTPException
from config import settings
from schemas.response import APIResponse, ResponseMetadata
from services.processor import process_file
from services.batch import batch_processor, MAX_BATCH_SIZE
from services.background import background_processor
from schemas.ocr import BatchItemResult, BatchStatus, SingleJobStatus


class OutputFormat(str, Enum):
    json = "json"
    markdown = "markdown"
    xml = "xml"


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

    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(413, "File too large")

    filename = cast(str, file.filename)
    content_type = cast(str, file.content_type)

    data, error, elapsed = await process_file(
        content, filename, content_type, output_format.value
    )

    if error:
        raise HTTPException(500, detail=error)

    return build_response(data, output_format, filename, content_type, elapsed)


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
):
    if len(file) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"Max {MAX_BATCH_SIZE} files per batch")
    if len(file) == 0:
        raise HTTPException(400, "At least one file required")

    files_data = [
        (cast(str, f.filename), cast(str, f.content_type), await f.read())
        for f in file
    ]
    batch_id = batch_processor.create_job(files_data, output_format.value)
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
