from unittest.mock import AsyncMock, patch

import pytest

from app.services.async_job import MAX_BATCH_SIZE, AsyncJob, AsyncJobProcessor


class TestAsyncJobBatchInit:
    def test_default_source_type_is_file(self):
        job = AsyncJob("b1", "json")
        job._files = [("f.pdf", "app/pdf", b"data")]
        job.total_files = 1
        assert job.source_type == "file"

    def test_source_type_stored(self):
        job = AsyncJob("b2", "json", source_type="url")
        job._files = ["https://example.com"]
        job.total_files = 1
        assert job.source_type == "url"

    def test_total_files_count(self):
        job = AsyncJob("b3", "json")
        job._files = [("a.pdf", "app/pdf", b"1"), ("b.pdf", "app/pdf", b"2")]
        job.total_files = 2
        assert job.total_files == 2

    def test_max_batch_size_constant(self):
        assert MAX_BATCH_SIZE == 20


class TestAsyncJobProcessorBatch:
    @pytest.fixture
    def bp(self):
        return AsyncJobProcessor()

    @pytest.mark.asyncio
    @patch("app.services.async_job.uuid.uuid4")
    async def test_create_batch_returns_id(self, mock_uuid, bp):
        mock_uuid.return_value.hex = "batch001"
        bid = bp.create_batch([("f.pdf", "app/pdf", b"x")], "json")
        assert bid == "batch001"
        assert bp.get_job(bid) is not None

    def test_get_job_returns_none_for_missing(self, bp):
        assert bp.get_job("no-such-batch") is None

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_url", new_callable=AsyncMock)
    async def test_run_batch_url_source(self, mock_process_url, bp):
        mock_process_url.return_value = ("result", None, 100.0)
        job = AsyncJob("b_url", "json", source_type="url")
        job._files = ["https://example.com"]
        job.total_files = 1
        job.results = [None]
        bp._jobs["b_url"] = job
        await bp._run_batch("b_url")
        mock_process_url.assert_awaited_once_with(
            "https://example.com", "json", options=None
        )
        assert job.status == "completed"

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_file", new_callable=AsyncMock)
    async def test_run_batch_file_source(self, mock_process_file, bp):
        mock_process_file.return_value = ("file_ok", None, 50.0)
        job = AsyncJob("b_file", "json")
        job._files = [("doc.pdf", "app/pdf", b"data")]
        job.total_files = 1
        job.results = [None]
        bp._jobs["b_file"] = job
        await bp._run_batch("b_file")
        mock_process_file.assert_awaited_once()
        assert job.results[0].success is True
        assert job.results[0].file_name == "doc.pdf"

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_html", new_callable=AsyncMock)
    async def test_run_batch_html_source(self, mock_process_html, bp):
        mock_process_html.return_value = ("html_ok", None, 60.0)
        job = AsyncJob("b_html", "json", source_type="html")
        job._files = [[("index.html", b"<h1>A</h1>")]]
        job.total_files = 1
        job.results = [None]
        bp._jobs["b_html"] = job
        await bp._run_batch("b_html")
        mock_process_html.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_url", new_callable=AsyncMock)
    async def test_run_batch_reports_error_per_item(self, mock_process_url, bp):
        mock_process_url.return_value = (None, "Failed", 30.0)
        job = AsyncJob("b_err", "json", source_type="url")
        job._files = ["https://example.com"]
        job.total_files = 1
        job.results = [None]
        bp._jobs["b_err"] = job
        await bp._run_batch("b_err")
        assert job.results[0].success is False
        assert job.results[0].error["code"] == "PROCESSING_ERROR"
