from unittest.mock import AsyncMock, patch

import pytest

from app.services.async_job import ASYNC_TTL, AsyncJob, AsyncJobProcessor


class TestAsyncJobInit:
    def test_default_source_type_is_file(self):
        job = AsyncJob("j1", "json", file_name="f.pdf", file_type="app/pdf")
        assert job.source_type == "file"
        assert job.extra_data is None

    def test_source_type_and_extra_data_stored(self):
        job = AsyncJob(
            "j2", "json", source_type="url", extra_data="https://example.com"
        )
        assert job.source_type == "url"
        assert job.extra_data == "https://example.com"

    def test_initial_status_pending(self):
        job = AsyncJob("j3", "json", file_name="f.pdf", file_type="app/pdf")
        assert job.status == "pending"

    def test_ttl_constant(self):
        assert ASYNC_TTL == 3600


class TestAsyncJobProcessor:
    @pytest.fixture
    def bp(self):
        return AsyncJobProcessor()

    @pytest.mark.asyncio
    @patch("app.services.async_job.uuid.uuid4")
    async def test_create_job_returns_id_and_stores_job(self, mock_uuid, bp):
        mock_uuid.return_value.hex = "abc123def456"
        jid = bp.create_job("f.pdf", "app/pdf", "json")
        assert jid == "abc123def456"
        assert bp.get_job(jid) is not None
        assert bp.get_job(jid).file_name == "f.pdf"

    @pytest.mark.asyncio
    @patch("app.services.async_job.uuid.uuid4")
    async def test_create_job_with_source_type(self, mock_uuid, bp):
        mock_uuid.return_value.hex = "xyz789"
        jid = bp.create_job(
            "url", "source/url", "json", source_type="url", extra_data="https://x.com"
        )
        job = bp.get_job(jid)
        assert job.source_type == "url"
        assert job.extra_data == "https://x.com"

    def test_get_job_returns_none_for_missing(self, bp):
        assert bp.get_job("does-not-exist") is None

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_url", new_callable=AsyncMock)
    async def test_run_job_url_source(self, mock_process_url, bp):
        mock_process_url.return_value = ("result", None, 100.0)
        job = AsyncJob(
            "j1", "json", source_type="url", extra_data="https://example.com"
        )
        bp._jobs["j1"] = job
        await bp._run_single("j1")
        mock_process_url.assert_awaited_once_with(
            "https://example.com", "json", options=None, version=None
        )
        assert job.status == "completed"
        assert job.data == "result"

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_file", new_callable=AsyncMock)
    async def test_run_job_file_source(self, mock_process_file, bp):
        mock_process_file.return_value = ("file_result", None, 50.0)
        job = AsyncJob(
            "j2",
            "json",
            file_name="doc.pdf",
            file_type="application/pdf",
            temp_path="/tmp/test.pdf",
        )
        bp._jobs["j2"] = job
        await bp._run_single("j2")
        mock_process_file.assert_awaited_once()
        assert job.status == "completed"

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_url", new_callable=AsyncMock)
    async def test_run_job_sets_error_on_failure(self, mock_process_url, bp):
        mock_process_url.return_value = (None, "Something broke", 200.0)
        job = AsyncJob("j3", "json", source_type="url", extra_data="https://x.com")
        bp._jobs["j3"] = job
        await bp._run_single("j3")
        assert job.status == "failed"
        assert job.error["code"] == "PROCESSING_ERROR"

    @pytest.mark.asyncio
    @patch("app.services.async_job.process_html", new_callable=AsyncMock)
    async def test_run_job_html_source(self, mock_process_html, bp):
        mock_process_html.return_value = ("html_result", None, 75.0)
        job = AsyncJob("j4", "json", source_type="html", extra_data=[("f", b"c")])
        bp._jobs["j4"] = job
        await bp._run_single("j4")
        mock_process_html.assert_awaited_once()
