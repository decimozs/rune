"""In-memory async single-job queue.

Jobs are stored in a plain dict and processed via fire-and-forget
asyncio tasks. Completed/failed jobs are evicted after 1 hour TTL.

For file source type, content is stored on disk (temp_path) instead
of in memory to avoid retaining large byte buffers for the job's
lifetime (up to 1 hour TTL). URL and HTML source types store their
data in extra_data as before (negligible memory).
"""

import uuid
import time
import asyncio
import contextlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

from services.processor import process_file, process_url, process_html

logger = logging.getLogger(__name__)

BACKGROUND_TTL = 3600


class BackgroundJob:
    """Represents a single background OCR job.

    status transitions: pending -> processing -> completed | failed.

    For 'file' source_type, content lives on disk at ``temp_path``
    (set by the route handler before calling create_job). This avoids
    holding large byte buffers in memory for the job's TTL.
    """

    def __init__(
        self,
        job_id: str,
        file_name: str,
        file_type: str,
        output_format: str,
        source_type: str = "file",
        temp_path: Optional[str] = None,
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
        self.temp_path = temp_path
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
        self,
        file_name: str,
        file_type: str,
        output_format: str,
        source_type: str = "file",
        temp_path: Optional[str] = None,
        extra_data: Any = None,
        output_options: Optional[dict] = None,
    ) -> str:
        """Create a job and start processing it in the background.

        For file source type, ``temp_path`` must point to a file already
        on disk (written by the route handler). URL/HTML source types
        pass data via ``extra_data``.

        Returns the job ID immediately. Processing happens in a
        fire-and-forget asyncio task. The caller polls GET /jobs/{id}
        to check completion.
        """
        job_id = uuid.uuid4().hex[:12]
        job = BackgroundJob(
            job_id,
            file_name,
            file_type,
            output_format,
            source_type,
            temp_path,
            extra_data,
            output_options,
        )
        self._jobs[job_id] = job
        asyncio.create_task(self._run_job(job_id))
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

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Return the job or None if not found or already expired."""
        return self._jobs.get(job_id)

    async def _run_job(self, job_id: str):
        """Execute the actual OCR processing. Dispatches by source_type.

        Wrapped in try/except so unexpected exceptions are captured as
        job failures instead of silently killing the task. CancelledError
        (shutdown) propagates — it is a BaseException, not Exception.
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
                    Path(job.temp_path), job.file_name, job.file_type,
                    job.output_format, options=job.output_options,
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
            job.completed_at = datetime.now(timezone.utc)

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
            job.completed_at = datetime.now(timezone.utc)


background_processor = BackgroundProcessor()
