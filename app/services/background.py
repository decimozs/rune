"""In-memory async single-job queue.

Jobs are stored in a plain dict and processed via fire-and-forget
asyncio tasks. Completed/failed jobs are evicted after 1 hour TTL.

This is in-memory only — all jobs are lost on application restart.
No persistence layer exists yet.
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

BACKGROUND_TTL = 3600


class BackgroundJob:
    """Represents a single background OCR job.

    Stores file content in memory (_content bytes) which can be
    large for big files. status transitions: pending -> processing
    -> completed | failed.
    """

    def __init__(
        self,
        job_id: str,
        file_name: str,
        file_type: str,
        content: bytes,
        output_format: str,
        source_type: str = "file",
        extra_data: Any = None,
        output_options: Optional[dict] = None,
    ):
        self.id = job_id
        self.status = "pending"
        self.file_name = file_name
        self.file_type = file_type
        self.output_format = output_format
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.processing_time_ms: Optional[float] = None
        self.data: Any = None
        self.error: Optional[dict] = None
        self._content = content
        self.source_type = source_type
        self.extra_data = extra_data
        self.output_options = output_options


class BackgroundProcessor:
    """Manages the job queue and cleanup loop."""

    def __init__(self):
        self._jobs: dict[str, BackgroundJob] = {}
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
        """Every 60s, remove jobs that completed/failed more than TTL ago."""
        while True:
            await asyncio.sleep(60)
            now = datetime.now(timezone.utc)
            expired = [
                jid
                for jid, job in self._jobs.items()
                if job.status in ("completed", "failed")
                and job.completed_at
                and (now - job.completed_at).total_seconds() > BACKGROUND_TTL
            ]
            for jid in expired:
                del self._jobs[jid]
                logger.info("Expired background job %s", jid)

    def create_job(
        self, file_name: str, file_type: str, content: bytes, output_format: str,
        source_type: str = "file", extra_data: Any = None,
        output_options: Optional[dict] = None,
    ) -> str:
        """Create a job and start processing it in the background.

        Returns the job ID immediately. Processing happens in a
        fire-and-forget asyncio task. The caller polls GET /jobs/{id}
        to check completion.
        """
        job_id = uuid.uuid4().hex[:12]
        job = BackgroundJob(job_id, file_name, file_type, content, output_format, source_type, extra_data, output_options)
        self._jobs[job_id] = job
        asyncio.create_task(self._run_job(job_id))
        logger.info("Created background job: id=%s, name=%s, type=%s, size=%d, source=%s", job_id, file_name, file_type, len(content), source_type)
        return job_id

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Return the job or None if not found or already expired."""
        return self._jobs.get(job_id)

    async def _run_job(self, job_id: str):
        """Execute the actual OCR processing. Dispatches by source_type."""
        job = self._jobs[job_id]
        job.status = "processing"
        start = time.time()
        logger.info("Processing background job: id=%s, source=%s", job_id, job.source_type)

        if job.source_type == "url":
            data, error, elapsed = await process_url(job.extra_data, job.output_format, options=job.output_options)
        elif job.source_type == "html":
            data, error, elapsed = await process_html(job.extra_data, job.output_format, options=job.output_options)
        else:
            fn, ct, content = job.file_name, job.file_type, job._content
            data, error, elapsed = await process_file(content, fn, ct, job.output_format, options=job.output_options)

        if error:
            job.error = {"code": "PROCESSING_ERROR", "message": error}
            job.status = "failed"
            logger.error("Background job failed: id=%s, error=%s, duration=%sms", job_id, error, elapsed)
        else:
            job.data = data
            job.status = "completed"
            logger.info("Background job completed: id=%s, duration=%sms", job_id, elapsed)

        job.processing_time_ms = elapsed
        job.completed_at = datetime.now(timezone.utc)


background_processor = BackgroundProcessor()
