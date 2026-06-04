"""All OCR API endpoints grouped by source type:

File endpoints  (/parse, /parse/jobs, /parse/batch)
URL endpoints   (/parse/url, /parse/url/jobs, /parse/url/batch)
HTML endpoints  (/parse/html, /parse/html/jobs, /parse/html/batch)

Each group has sync, background job, and batch variants.
All POST + GET job/batch endpoints require X-API-Key auth
(except health endpoints in routes/health.py).

For background and batch file uploads, content is written to a temp
file immediately in the route handler to avoid holding large byte
buffers in memory for the job's TTL lifetime.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import cast

from config import SUPPORTED_MODELS, settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from schemas.ocr import BatchItemResult, BatchStatus, JsonOutputOptions, SingleJobStatus
from schemas.response import APIResponse, ResponseMetadata
from services.async_job import MAX_BATCH_SIZE, async_job_processor
from services.auth import verify_api_key
from services.processor import process_file, process_html, process_url


def _split_group_by_html(
    entries: list[tuple[str, bytes]],
) -> list[list[tuple[str, bytes]]]:
    """Split uploaded files into groups by HTML file boundary.

    Each group starts with an .html/.htm file and includes subsequent
    non-HTML files as its assets. Assets uploaded before the first
    HTML file are dropped (orphans with no parent).
    """
    items = []
    current = []
    for name, content in entries:
        if name.endswith((".html", ".htm")):
            if current:
                items.append(current)
            current = [(name, content)]
        else:
            if current:
                current.append((name, content))
    if current:
        items.append(current)
    # drop groups with no HTML file (assets orphaned before first HTML)
    return [g for g in items if any(n.endswith((".html", ".htm")) for n, _ in g)]


class OutputFormat(StrEnum):
    json = "json"
    markdown = "markdown"
    xml = "xml"


router = APIRouter(prefix="/ocr", tags=["ocr"])


def validate_upload(file: UploadFile) -> None:
    """Check file has a name and its MIME type is in the allowed list."""
    if not file.filename:
        raise HTTPException(400, "Missing filename")
    if file.content_type not in settings.allowed_types_list:
        raise HTTPException(
            415,
            f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(settings.allowed_types_list)}",
        )


def resolve_model(model: str | None) -> str:
    """Validate and resolve model version.

    Returns the model string if valid, or the default from settings.
    Raises HTTP 400 for unsupported values.
    """
    resolved = model or settings.version
    if resolved not in SUPPORTED_MODELS:
        raise HTTPException(
            400,
            f"Unsupported model: {resolved}. Supported: {', '.join(SUPPORTED_MODELS)}",
        )
    return resolved


def build_response(
    data,
    output_format: OutputFormat,
    filename: str,
    content_type: str,
    elapsed: float,
    model: str = "",
) -> dict:
    """Wrap sync OCR result in APIResponse envelope with metadata."""
    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=model or settings.version,
            format=output_format.value,
            processing_time_ms=elapsed,
            file_name=filename,
            file_type=content_type,
        ),
        data=data,
    ).model_dump(exclude_none=True)


def _build_options(output_format: OutputFormat, **kwargs) -> dict | None:
    """Build JsonOutputOptions dict only for JSON format.

    Markdown and XML always include all fields regardless of query params.
    Returns None for non-JSON formats, meaning no field filtering.
    """
    if output_format != OutputFormat.json:
        return None
    return JsonOutputOptions(**kwargs).model_dump()


# ---------------------------------------------------------------------------
# File upload endpoints (image, PDF, office docs)
# ---------------------------------------------------------------------------


@router.post("/parse")
async def parse_file(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(default=OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """OCR a single uploaded file. Returns result synchronously."""
    resolved_model = resolve_model(model)
    validate_upload(file)

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    if len(content) > settings.max_file_size:
        raise HTTPException(413, "File too large")

    filename = cast(str, file.filename)
    content_type = cast(str, file.content_type)
    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )

    data, error, elapsed = await process_file(
        content,
        filename,
        content_type,
        output_format.value,
        options=opts,
        version=resolved_model,
    )

    if error:
        raise HTTPException(500, detail=error)

    return build_response(
        data, output_format, filename, content_type, elapsed, model=resolved_model
    )


@router.post("/parse/jobs", status_code=202)
async def create_job(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """Upload a file for background OCR. Returns job ID immediately (202)."""
    resolved_model = resolve_model(model)
    validate_upload(file)

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    if len(content) > settings.max_file_size:
        raise HTTPException(413, "File too large")

    filename = cast(str, file.filename)
    content_type = cast(str, file.content_type)

    stem = uuid.uuid4().hex
    safe = settings.upload_dir_path / f"{stem}_{Path(filename).name}"
    safe.write_bytes(content)
    try:
        opts = _build_options(
            output_format,
            include_bbox=include_bbox,
            include_confidence=include_confidence,
            include_extracted_text=include_extracted_text,
            include_page_image=include_page_image,
        )

        job_id = async_job_processor.create_job(
            filename,
            content_type,
            output_format.value,
            source_type="file",
            temp_path=str(safe),
            output_options=opts,
            model=resolved_model,
        )
        job = async_job_processor.get_job(job_id)
    except Exception:
        safe.unlink(missing_ok=True)
        raise

    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=resolved_model,
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
async def get_job_status(
    job_id: str,
    identity: str | None = Depends(verify_api_key),
):
    """Poll a background job's status and result."""
    job = async_job_processor.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")

    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=job.model or settings.version,
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
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """Upload multiple files for batch OCR. Returns batch ID immediately (202)."""
    resolved_model = resolve_model(model)
    if len(file) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"Max {MAX_BATCH_SIZE} files per batch")
    if len(file) == 0:
        raise HTTPException(400, "At least one file required")

    files_data = []
    for f in file:
        validate_upload(f)
        content = await f.read()
        if not content:
            raise HTTPException(400, f"Empty file: {f.filename}")
        if len(content) > settings.max_file_size:
            raise HTTPException(413, f"File too large: {f.filename}")
        stem = uuid.uuid4().hex
        safe = settings.upload_dir_path / f"{stem}_{Path(cast(str, f.filename)).name}"
        safe.write_bytes(content)
        files_data.append((cast(str, f.filename), cast(str, f.content_type), str(safe)))
    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )
    batch_id = async_job_processor.create_batch(
        files_data, output_format.value, output_options=opts, model=resolved_model
    )
    job = async_job_processor.get_job(batch_id)

    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=resolved_model,
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
async def get_batch_status(
    batch_id: str,
    identity: str | None = Depends(verify_api_key),
):
    """Poll a batch job's status with per-item results."""
    job = async_job_processor.get_job(batch_id)
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
            timestamp=datetime.now(UTC),
            model=job.model or settings.version,
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


# ---------------------------------------------------------------------------
# URL source endpoints  (Gotenberg Chromium -> PDF -> OCR)
# ---------------------------------------------------------------------------


@router.post("/parse/url")
async def parse_url(
    url: str = Form(...),
    output_format: OutputFormat = Query(default=OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """OCR a web page URL. Returns result synchronously."""
    resolved_model = resolve_model(model)
    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )
    data, error, elapsed = await process_url(
        url, output_format.value, options=opts, version=resolved_model
    )
    if error:
        raise HTTPException(500, detail=error)
    return build_response(
        data, output_format, url, "source/url", elapsed, model=resolved_model
    )


@router.post("/parse/url/jobs", status_code=202)
async def create_url_job(
    url: str = Form(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """Submit a URL for background OCR. Returns job ID immediately (202)."""
    resolved_model = resolve_model(model)
    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )
    job_id = async_job_processor.create_job(
        url,
        "source/url",
        output_format.value,
        source_type="url",
        extra_data=url,
        output_options=opts,
        model=resolved_model,
    )
    job = async_job_processor.get_job(job_id)
    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=resolved_model,
            format=output_format.value,
        ),
        data={
            "job_id": job_id,
            "status": job.status,
            "file_name": url,
            "file_type": "source/url",
            "created_at": job.created_at.isoformat(),
        },
    ).model_dump(exclude_none=True)


@router.post("/parse/url/batch", status_code=202)
async def parse_url_batch(
    url: list[str] = Form(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """Submit multiple URLs for batch OCR. Returns batch ID immediately (202)."""
    resolved_model = resolve_model(model)
    if len(url) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"Max {MAX_BATCH_SIZE} URLs per batch")
    if len(url) == 0:
        raise HTTPException(400, "At least one URL required")
    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )
    batch_id = async_job_processor.create_batch(
        url,
        output_format.value,
        source_type="url",
        output_options=opts,
        model=resolved_model,
    )
    job = async_job_processor.get_job(batch_id)
    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=resolved_model,
            format=output_format.value,
        ),
        data={
            "batch_id": batch_id,
            "status": job.status,
            "total_files": job.total_files,
            "created_at": job.created_at.isoformat(),
        },
    ).model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# HTML source endpoints  (upload .html file + assets, Gotenberg -> PDF -> OCR)
# ---------------------------------------------------------------------------


@router.post("/parse/html")
async def parse_html(
    files: list[UploadFile] = File(...),
    output_format: OutputFormat = Query(default=OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """OCR an uploaded HTML file with assets. Returns result synchronously."""
    resolved_model = resolve_model(model)
    if not files:
        raise HTTPException(400, "At least one file required (index.html)")
    file_tuples = []
    for f in files:
        content = await f.read()
        if not content:
            raise HTTPException(400, f"Empty file: {f.filename}")
        if len(content) > settings.max_file_size:
            raise HTTPException(413, f"File too large: {f.filename}")
        file_tuples.append((cast(str, f.filename), content))
    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )
    data, error, elapsed = await process_html(
        file_tuples, output_format.value, options=opts, version=resolved_model
    )
    if error:
        raise HTTPException(500, detail=error)
    return build_response(
        data, output_format, "index.html", "source/html", elapsed, model=resolved_model
    )


@router.post("/parse/html/jobs", status_code=202)
async def create_html_job(
    files: list[UploadFile] = File(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """Submit HTML + assets for background OCR. Returns job ID immediately (202)."""
    resolved_model = resolve_model(model)
    if not files:
        raise HTTPException(400, "At least one file required (index.html)")
    file_tuples = []
    for f in files:
        content = await f.read()
        if not content:
            raise HTTPException(400, f"Empty file: {f.filename}")
        if len(content) > settings.max_file_size:
            raise HTTPException(413, f"File too large: {f.filename}")
        file_tuples.append((cast(str, f.filename), content))
    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )
    job_id = async_job_processor.create_job(
        "index.html",
        "source/html",
        output_format.value,
        source_type="html",
        extra_data=file_tuples,
        output_options=opts,
        model=resolved_model,
    )
    job = async_job_processor.get_job(job_id)
    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=resolved_model,
            format=output_format.value,
        ),
        data={
            "job_id": job_id,
            "status": job.status,
            "file_name": "index.html",
            "file_type": "source/html",
            "created_at": job.created_at.isoformat(),
        },
    ).model_dump(exclude_none=True)


@router.post("/parse/html/batch", status_code=202)
async def parse_html_batch(
    files: list[UploadFile] = File(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    include_bbox: bool = Query(True),
    include_confidence: bool = Query(True),
    include_extracted_text: bool = Query(True),
    include_page_image: bool = Query(True),
    model: str | None = Query(default=None),
    identity: str | None = Depends(verify_api_key),
):
    """Upload multiple HTML file groups for batch OCR. Returns batch ID immediately (202).

    Files are grouped by HTML boundary via _split_group_by_html so
    each HTML file plus its assets forms one batch item.
    """
    resolved_model = resolve_model(model)
    file_tuples = []
    for f in files:
        content = await f.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(413, f"File too large: {f.filename}")
        file_tuples.append((cast(str, f.filename), content))

    items = _split_group_by_html(file_tuples)
    if not items:
        raise HTTPException(400, "At least one HTML file required")
    if len(items) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"Max {MAX_BATCH_SIZE} file sets per batch")

    opts = _build_options(
        output_format,
        include_bbox=include_bbox,
        include_confidence=include_confidence,
        include_extracted_text=include_extracted_text,
        include_page_image=include_page_image,
    )
    batch_id = async_job_processor.create_batch(
        items,
        output_format.value,
        source_type="html",
        output_options=opts,
        model=resolved_model,
    )
    job = async_job_processor.get_job(batch_id)
    return APIResponse(
        success=True,
        metadata=ResponseMetadata(
            timestamp=datetime.now(UTC),
            model=resolved_model,
            format=output_format.value,
        ),
        data={
            "batch_id": batch_id,
            "status": job.status,
            "total_files": job.total_files,
            "created_at": job.created_at.isoformat(),
        },
    ).model_dump(exclude_none=True)
