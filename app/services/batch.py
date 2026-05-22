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

MAX_BATCH_SIZE = 20
RESULTS_TTL = 3600
DEFAULT_CONCURRENCY = 2


class BatchItemResult:
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
    def __init__(self, batch_id: str, files: list, output_format: str, concurrency: int):
        self.id = batch_id
        self.status = "pending"
        self.output_format = output_format
        self.total_files = len(files)
        self.concurrency = concurrency
        self.results: list[Optional[BatchItemResult]] = [None] * len(files)
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.processing_time_ms: Optional[float] = None
        self._files = files


class BatchProcessor:
    def __init__(self):
        self._jobs: dict[str, BatchJob] = {}
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
                bid
                for bid, job in self._jobs.items()
                if job.status == "completed"
                and job.completed_at
                and (now - job.completed_at).total_seconds() > RESULTS_TTL
            ]
            for bid in expired:
                del self._jobs[bid]
                logger.info("Expired batch %s", bid)

    def create_job(self, files: list, output_format: str, concurrency: int) -> str:
        batch_id = uuid.uuid4().hex[:12]
        job = BatchJob(batch_id, files, output_format, min(concurrency, 4))
        self._jobs[batch_id] = job
        asyncio.create_task(self._run_job(batch_id))
        return batch_id

    def get_job(self, batch_id: str) -> Optional[BatchJob]:
        return self._jobs.get(batch_id)

    async def _run_job(self, batch_id: str):
        import magic
        from pathlib import Path

        job = self._jobs[batch_id]
        job.status = "processing"
        start = time.time()

        async def process_one(index: int):
            fn, ct, content = job._files[index]
            f_start = time.time()

            async def work():
                safe = Path(settings.upload_dir) / f"{uuid.uuid4().hex}_{fn}"
                safe.write_bytes(content)

                detected = magic.from_file(str(safe), mime=True)
                if detected not in settings.allowed_types_list:
                    safe.unlink(missing_ok=True)
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

                safe.unlink(missing_ok=True)
                return result_data

            try:
                data = await work()
                elapsed = round((time.time() - f_start) * 1000, 2)
                job.results[index] = BatchItemResult(
                    file_name=fn,
                    file_type=ct,
                    processing_time_ms=elapsed,
                    success=True,
                    data=data,
                )
            except Exception as e:
                elapsed = round((time.time() - f_start) * 1000, 2)
                job.results[index] = BatchItemResult(
                    file_name=fn,
                    file_type=ct,
                    processing_time_ms=elapsed,
                    success=False,
                    error={"code": type(e).__name__, "message": str(e)},
                )

        for i in range(job.total_files):
            await process_one(i)
        job.processing_time_ms = round((time.time() - start) * 1000, 2)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        logger.info("Batch %s completed in %sms", batch_id, job.processing_time_ms)


batch_processor = BatchProcessor()
