"""Combined async processor for single-job and batch OCR.

Merges the previous BackgroundProcessor (single-item jobs) and
BatchProcessor (multi-item jobs) into one module. Shared lifecycle:
start/stop/cleanup loop/TTL dispatch are written once instead of
twice.

Single-item jobs (create_job): fire-and-forget, one process_* call.
Batch jobs (create_batch): sequential per-item processing with
error isolation. Both types share the same cleanup loop.
"""

import asyncio
import contextlib
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.processor import process_file, process_html, process_url

logger = logging.getLogger(__name__)

ASYNC_TTL = 3600
MAX_BATCH_SIZE = 20


class BatchItemResult:
    """Result for a single file within a batch. success=False if processing failed."""

    def __init__(
        self,
        file_name: str,
        file_type: str,
        processing_time_ms: float,
        success: bool,
        data: Any = None,
        error: dict | None = None,
    ):
        self.file_name = file_name
        self.file_type = file_type
        self.processing_time_ms = processing_time_ms
        self.success = success
        self.data = data
        self.error = error


class AsyncJob:
    """Represents a single async OCR job (single-item or batch).

    status transitions: pending -> processing -> completed | failed.

    Single-item jobs (created via create_job):
        file_name, file_type, data, error, temp_path, extra_data are used.

    Batch jobs (created via create_batch):
        results, total_files, _files are used.
    """

    def __init__(
        self,
        job_id: str,
        output_format: str,
        source_type: str = "file",
        output_options: dict | None = None,
        file_name: str | None = None,
        file_type: str | None = None,
        temp_path: str | None = None,
        extra_data: Any = None,
    ):
        self.id = job_id
        self.status = "pending"
        self.output_format = output_format
        self.source_type = source_type
        self.output_options = output_options
        self.created_at = datetime.now(UTC)
        self.completed_at: datetime | None = None
        self.processing_time_ms: float | None = None

        self.file_name = file_name
        self.file_type = file_type
        self.data: Any = None
        self.error: dict | None = None
        self.temp_path = temp_path
        self.extra_data = extra_data

        self.total_files: int = 0
        self.results: list[BatchItemResult | None] = []
        self._files: list = []


class AsyncJobProcessor:
    """Manages async job queue for both single-job and batch OCR."""

    def __init__(self):
        self._jobs: dict[str, AsyncJob] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def start(self):
        """Start the TTL-based cleanup loop. Called in lifespan."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop the cleanup loop. Called in lifespan shutdown."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def _cleanup_loop(self):
        """Every 60s, remove jobs that completed/failed more than TTL ago."""
        while True:
            await asyncio.sleep(60)
            now = datetime.now(UTC)
            expired = [
                jid
                for jid, job in self._jobs.items()
                if job.status in ("completed", "failed")
                and job.completed_at
                and (now - job.completed_at).total_seconds() > ASYNC_TTL
            ]
            for jid in expired:
                del self._jobs[jid]
                logger.info("Expired async job %s", jid)

    def create_job(
        self,
        file_name: str,
        file_type: str,
        output_format: str,
        source_type: str = "file",
        temp_path: str | None = None,
        extra_data: Any = None,
        output_options: dict | None = None,
    ) -> str:
        """Create a single-item background job.

        For file source type, ``temp_path`` must point to a file already
        on disk (written by the route handler). URL/HTML source types
        pass data via ``extra_data``.

        Returns the job ID immediately. Processing happens in a
        fire-and-forget asyncio task. The caller polls GET /jobs/{id}
        to check completion.
        """
        job_id = uuid.uuid4().hex[:12]
        job = AsyncJob(job_id, output_format, source_type, output_options)
        job.file_name = file_name
        job.file_type = file_type
        job.temp_path = temp_path
        job.extra_data = extra_data
        job.total_files = 1
        self._jobs[job_id] = job
        asyncio.create_task(self._run_single(job_id))
        size_info = Path(temp_path).stat().st_size if temp_path else 0
        logger.info(
            "Created background job: id=%s, name=%s, type=%s, size=%d, source=%s",
            job_id,
            file_name,
            file_type,
            size_info,
            source_type,
        )
        return job_id

    def create_batch(
        self,
        files: list,
        output_format: str,
        source_type: str = "file",
        output_options: dict | None = None,
    ) -> str:
        """Create a batch job with multiple items.

        Items processed sequentially. Returns batch ID immediately.
        The caller polls GET /batch/{id} to check completion.
        """
        batch_id = uuid.uuid4().hex[:12]
        job = AsyncJob(batch_id, output_format, source_type, output_options)
        job._files = files
        job.total_files = len(files)
        job.results = [None] * len(files)
        self._jobs[batch_id] = job
        asyncio.create_task(self._run_batch(batch_id))
        logger.info(
            "Created batch job: id=%s, files=%d, source=%s, format=%s",
            batch_id,
            len(files),
            source_type,
            output_format,
        )
        return batch_id

    def get_job(self, job_id: str) -> AsyncJob | None:
        """Return the job or None if not found or already expired."""
        return self._jobs.get(job_id)

    async def _run_single(self, job_id: str):
        """Execute a single-item background job.

        Dispatches by source_type to the appropriate processor function.
        Wrapped in try/except so unexpected exceptions are captured as
        job failures instead of silently killing the task. CancelledError
        (shutdown) propagates.
        """
        job = self._jobs[job_id]
        job.status = "processing"
        start = time.time()
        logger.info(
            "Processing background job: id=%s, source=%s", job_id, job.source_type
        )

        try:
            if job.source_type == "url":
                data, error, elapsed = await process_url(
                    job.extra_data, job.output_format, options=job.output_options
                )
            elif job.source_type == "html":
                data, error, elapsed = await process_html(
                    job.extra_data, job.output_format, options=job.output_options
                )
            else:
                data, error, elapsed = await process_file(
                    Path(job.temp_path),
                    job.file_name,
                    job.file_type,
                    job.output_format,
                    options=job.output_options,
                )

            if error:
                job.error = {"code": "PROCESSING_ERROR", "message": error}
                job.status = "failed"
                logger.error(
                    "Background job failed: id=%s, error=%s, duration=%sms",
                    job_id,
                    error,
                    elapsed,
                )
            else:
                job.data = data
                job.status = "completed"
                logger.info(
                    "Background job completed: id=%s, duration=%sms", job_id, elapsed
                )

            job.processing_time_ms = elapsed
            job.completed_at = datetime.now(UTC)

        except Exception:
            elapsed = round((time.time() - start) * 1000, 2)
            logger.exception(
                "Background job crashed: id=%s, duration=%sms", job_id, elapsed
            )
            job.error = {
                "code": "TASK_CRASH",
                "message": "Background task failed unexpectedly",
            }
            job.status = "failed"
            job.processing_time_ms = elapsed
            job.completed_at = datetime.now(UTC)

    async def _run_batch(self, batch_id: str):
        """Process batch items SEQUENTIALLY.

        Each item runs independently. Per-item exceptions are caught to
        preserve the invariant that one failure does not abort the batch.
        The outer try/except guards against unexpected failures in the
        loop logic itself.
        """
        job = self._jobs[batch_id]
        job.status = "processing"
        start = time.time()
        logger.info("Processing batch job: id=%s, files=%d", batch_id, job.total_files)

        try:

            async def process_one(index: int):
                try:
                    if job.source_type == "url":
                        url_str = job._files[index]
                        data, error, elapsed = await process_url(
                            url_str, job.output_format, options=job.output_options
                        )
                        fn = url_str
                        ct = "source/url"
                    elif job.source_type == "html":
                        data, error, elapsed = await process_html(
                            job._files[index],
                            job.output_format,
                            options=job.output_options,
                        )
                        fn = f"html_{index}"
                        ct = "source/html"
                    else:
                        fn, ct, data_or_path = job._files[index]
                        if isinstance(data_or_path, str):
                            content = Path(data_or_path)
                        else:
                            content = data_or_path
                        data, error, elapsed = await process_file(
                            content,
                            fn,
                            ct,
                            job.output_format,
                            options=job.output_options,
                        )
                    job.results[index] = BatchItemResult(
                        file_name=fn,
                        file_type=ct,
                        processing_time_ms=elapsed,
                        success=error is None,
                        data=data if error is None else None,
                        error={"code": "PROCESSING_ERROR", "message": error}
                        if error
                        else None,
                    )
                    if error:
                        logger.error(
                            "Batch item failed: batch=%s, index=%d, name=%s, "
                            "error=%s, duration=%sms",
                            batch_id,
                            index,
                            fn,
                            error,
                            elapsed,
                        )
                    else:
                        logger.info(
                            "Batch item done: batch=%s, index=%d, name=%s, "
                            "duration=%sms",
                            batch_id,
                            index,
                            fn,
                            elapsed,
                        )
                except Exception:
                    elapsed = round((time.time() - start) * 1000, 2)
                    logger.exception(
                        "Batch item crashed: batch=%s, index=%d", batch_id, index
                    )
                    job.results[index] = BatchItemResult(
                        file_name=f"item_{index}",
                        file_type="unknown",
                        processing_time_ms=elapsed,
                        success=False,
                        error={
                            "code": "ITEM_CRASH",
                            "message": "Item processing failed unexpectedly",
                        },
                    )

            for i in range(job.total_files):
                logger.info(
                    "Batch progress: batch=%s, item=%d/%d",
                    batch_id,
                    i + 1,
                    job.total_files,
                )
                await process_one(i)

        except Exception:
            logger.exception("Batch job crashed: id=%s", batch_id)
            job.status = "failed"

        job.processing_time_ms = round((time.time() - start) * 1000, 2)
        if job.status != "failed":
            job.status = "completed"
        job.completed_at = datetime.now(UTC)
        logger.info(
            "Batch completed: id=%s, files=%d, duration=%sms",
            batch_id,
            job.total_files,
            job.processing_time_ms,
        )


async_job_processor = AsyncJobProcessor()
