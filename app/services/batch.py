"""In-memory batch processor for multi-file OCR jobs.

Items are processed SEQUENTIALLY (not with asyncio.gather) to avoid
unbounded concurrency. The shared semaphore in processor.py provides
global fairness across all concurrent calls.

Per-item error isolation: one file failure does not abort the batch.
The batch always ends as completed, but individual items carry
success=True/False.
"""

import uuid
import time
import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from services.processor import process_file, process_url, process_html

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 20
RESULTS_TTL = 3600


class BatchItemResult:
    """Result for a single file within a batch. success=False if processing failed."""

    def __init__(
        self,
        file_name: str,
        file_type: str,
        processing_time_ms: float,
        success: bool,
        data: Any = None,
        error: Optional[dict] = None,
    ):
        self.file_name = file_name
        self.file_type = file_type
        self.processing_time_ms = processing_time_ms
        self.success = success
        self.data = data
        self.error = error


class BatchJob:
    """Represents a batch OCR job with multiple files."""

    def __init__(self, batch_id: str, files: list, output_format: str, source_type: str = "file", output_options: Optional[dict] = None):
        self.id = batch_id
        self.status = "pending"
        self.output_format = output_format
        self.total_files = len(files)
        # Pre-allocate result slots; filled in order as items complete
        self.results: list[Optional[BatchItemResult]] = [None] * len(files)
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.processing_time_ms: Optional[float] = None
        self._files = files
        self.source_type = source_type
        self.output_options = output_options


class BatchProcessor:
    """Manages the batch queue, sequential processing, and TTL cleanup."""

    def __init__(self):
        self._jobs: dict[str, BatchJob] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

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
        """Every 60s, remove batches that completed more than TTL ago."""
        while True:
            await asyncio.sleep(60)
            now = datetime.now(timezone.utc)
            expired = [
                bid
                for bid, job in self._jobs.items()
                if job.status == "completed"
                and job.completed_at
                and (now - job.completed_at).total_seconds() > RESULTS_TTL
            ]
            for bid in expired:
                del self._jobs[bid]
                logger.info("Expired batch %s", bid)

    def create_job(self, files: list, output_format: str, source_type: str = "file", output_options: Optional[dict] = None) -> str:
        """Create a batch job and start processing. Returns batch ID immediately."""
        batch_id = uuid.uuid4().hex[:12]
        job = BatchJob(batch_id, files, output_format, source_type, output_options)
        self._jobs[batch_id] = job
        asyncio.create_task(self._run_job(batch_id))
        logger.info("Created batch job: id=%s, files=%d, source=%s, format=%s", batch_id, len(files), source_type, output_format)
        return batch_id

    def get_job(self, batch_id: str) -> Optional[BatchJob]:
        """Return the batch or None if not found or already expired."""
        return self._jobs.get(batch_id)

    async def _run_job(self, batch_id: str):
        """Process batch items SEQUENTIALLY. Each item runs independently."""
        job = self._jobs[batch_id]
        job.status = "processing"
        start = time.time()
        logger.info("Processing batch job: id=%s, files=%d", batch_id, job.total_files)

        async def process_one(index: int):
            """Process a single batch item by source type."""
            if job.source_type == "url":
                url_str = job._files[index]
                data, error, elapsed = await process_url(url_str, job.output_format, options=job.output_options)
                fn = url_str
                ct = "source/url"
            elif job.source_type == "html":
                data, error, elapsed = await process_html(job._files[index], job.output_format, options=job.output_options)
                fn = f"html_{index}"
                ct = "source/html"
            else:
                fn, ct, content = job._files[index]
                data, error, elapsed = await process_file(
                    content, fn, ct, job.output_format, options=job.output_options
                )
            job.results[index] = BatchItemResult(
                file_name=fn,
                file_type=ct,
                processing_time_ms=elapsed,
                success=error is None,
                data=data if error is None else None,
                error={"code": "PROCESSING_ERROR", "message": error} if error else None,
            )
            if error:
                logger.error("Batch item failed: batch=%s, index=%d, name=%s, error=%s, duration=%sms", batch_id, index, fn, error, elapsed)
            else:
                logger.info("Batch item done: batch=%s, index=%d, name=%s, duration=%sms", batch_id, index, fn, elapsed)

        for i in range(job.total_files):
            logger.info("Batch progress: batch=%s, item=%d/%d", batch_id, i + 1, job.total_files)
            await process_one(i)

        job.processing_time_ms = round((time.time() - start) * 1000, 2)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        logger.info("Batch completed: id=%s, files=%d, duration=%sms", batch_id, job.total_files, job.processing_time_ms)


batch_processor = BatchProcessor()
