import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from config import settings
from services.converter import converter
from services.ocr import ocr_service

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


class BackgroundProcessor:
    def __init__(self):
        self._jobs: dict[str, BackgroundJob] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()

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
        self, file_name: str, file_type: str, content: bytes, output_format: str
    ) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = BackgroundJob(job_id, file_name, file_type, content, output_format)
        self._jobs[job_id] = job
        asyncio.create_task(self._run_job(job_id))
        return job_id

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        return self._jobs.get(job_id)

    async def _run_job(self, job_id: str):
        import magic
        from pathlib import Path

        job = self._jobs[job_id]
        job.status = "processing"
        start = time.time()

        try:
            fn = job.file_name
            ct = job.file_type
            content = job._content

            safe = Path(settings.upload_dir) / f"{uuid.uuid4().hex}_{fn}"
            safe.write_bytes(content)

            try:
                detected = magic.from_file(str(safe), mime=True)
                if detected not in settings.allowed_types_list:
                    raise ValueError(f"Unsupported type: {detected}")

                if converter.needs_conversion(detected):
                    safe = await converter.to_pdf(safe, detected)
                    detected = "application/pdf"

                if job.output_format == "markdown":
                    result_data = await asyncio.to_thread(
                        ocr_service.to_markdown, str(safe), fn, detected
                    )
                else:
                    result_data = await asyncio.to_thread(
                        ocr_service.process, str(safe), fn, detected
                    )

            finally:
                safe.unlink(missing_ok=True)

            elapsed = round((time.time() - start) * 1000, 2)
            job.processing_time_ms = elapsed
            job.data = result_data
            job.status = "completed"

        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            job.processing_time_ms = elapsed
            job.error = {"code": type(e).__name__, "message": str(e)}
            job.status = "failed"

        job.completed_at = datetime.now(timezone.utc)
        logger.info(
            "Background job %s %s in %sms",
            job_id,
            job.status,
            job.processing_time_ms,
        )


background_processor = BackgroundProcessor()
