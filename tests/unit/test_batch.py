from unittest.mock import AsyncMock, patch

import pytest

from app.services.batch import BatchProcessor, BatchJob, MAX_BATCH_SIZE


class TestBatchJobInit:
    def test_default_source_type_is_file(self):
        job = BatchJob("b1", [("f.pdf", "app/pdf", b"data")], "json")
        assert job.source_type == "file"

    def test_source_type_stored(self):
        job = BatchJob("b2", ["https://example.com"], "json", source_type="url")
        assert job.source_type == "url"

    def test_total_files_count(self):
        files = [("a.pdf", "app/pdf", b"1"), ("b.pdf", "app/pdf", b"2")]
        job = BatchJob("b3", files, "json")
        assert job.total_files == 2

    def test_max_batch_size_constant(self):
        assert MAX_BATCH_SIZE == 20


class TestBatchProcessor:
    @pytest.fixture
    def bp(self):
        return BatchProcessor()

    @pytest.mark.asyncio
    @patch("app.services.batch.uuid.uuid4")
    async def test_create_job_returns_id(self, mock_uuid, bp):
        mock_uuid.return_value.hex = "batch001"
        bid = bp.create_job([("f.pdf", "app/pdf", b"x")], "json")
        assert bid == "batch001"
        assert bp.get_job(bid) is not None

    def test_get_job_returns_none_for_missing(self, bp):
        assert bp.get_job("no-such-batch") is None

    @pytest.mark.asyncio
    @patch("app.services.batch.process_url", new_callable=AsyncMock)
    async def test_run_job_url_source(self, mock_process_url, bp):
        mock_process_url.return_value = ("result", None, 100.0)
        job = BatchJob("b_url", ["https://example.com"], "json", source_type="url")
        bp._jobs["b_url"] = job
        await bp._run_job("b_url")
        mock_process_url.assert_awaited_once_with("https://example.com", "json", options=None)
        assert job.status == "completed"

    @pytest.mark.asyncio
    @patch("app.services.batch.process_file", new_callable=AsyncMock)
    async def test_run_job_file_source(self, mock_process_file, bp):
        mock_process_file.return_value = ("file_ok", None, 50.0)
        job = BatchJob("b_file", [("doc.pdf", "app/pdf", b"data")], "json")
        bp._jobs["b_file"] = job
        await bp._run_job("b_file")
        mock_process_file.assert_awaited_once()
        assert job.results[0].success is True
        assert job.results[0].file_name == "doc.pdf"

    @pytest.mark.asyncio
    @patch("app.services.batch.process_html", new_callable=AsyncMock)
    async def test_run_job_html_source(self, mock_process_html, bp):
        mock_process_html.return_value = ("html_ok", None, 60.0)
        job = BatchJob("b_html", [[("index.html", b"<h1>A</h1>")]], "json", source_type="html")
        bp._jobs["b_html"] = job
        await bp._run_job("b_html")
        mock_process_html.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.batch.process_url", new_callable=AsyncMock)
    async def test_run_job_reports_error_per_item(self, mock_process_url, bp):
        mock_process_url.return_value = (None, "Failed", 30.0)
        job = BatchJob("b_err", ["https://example.com"], "json", source_type="url")
        bp._jobs["b_err"] = job
        await bp._run_job("b_err")
        assert job.results[0].success is False
        assert job.results[0].error["code"] == "PROCESSING_ERROR"
