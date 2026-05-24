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
    def __init__(self):
        self._jobs: dict[str, BackgroundJob] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def _cleanup_loop(self):
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
        job_id = uuid.uuid4().hex[:12]
        job = BackgroundJob(job_id, file_name, file_type, content, output_format, source_type, extra_data, output_options)
        self._jobs[job_id] = job
        asyncio.create_task(self._run_job(job_id))
        return job_id

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        return self._jobs.get(job_id)

    async def _run_job(self, job_id: str):
        job = self._jobs[job_id]
        job.status = "processing"
        start = time.time()

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
        else:
            job.data = data
            job.status = "completed"

        job.processing_time_ms = elapsed
        job.completed_at = datetime.now(timezone.utc)
        logger.info("Background job %s %s in %sms", job_id, job.status, elapsed)


background_processor = BackgroundProcessor()
