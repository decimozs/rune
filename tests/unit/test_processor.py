from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.processor import TEXT_BASED_TYPES, _ocr_semaphore


class TestTextBasedTypes:
    @pytest.mark.parametrize(
        ("mime", "expected"),
        [
            ("text/csv", True),
            ("text/rtf", True),
            ("text/plain", True),
            ("application/pdf", False),
            ("image/png", False),
        ],
    )
    def test_text_based_types(self, mime, expected):
        assert (mime in TEXT_BASED_TYPES) == expected


class TestSemaphore:
    def test_semaphore_value_from_config(self):
        from app.config import settings

        assert _ocr_semaphore._value == settings.max_concurrent_jobs
        assert _ocr_semaphore._value >= 1


class TestProcessUrl:
    @patch("app.services.processor.uuid.uuid4")
    @patch("app.services.processor.converter")
    @patch("app.services.processor.ocr_service")
    @patch("app.services.processor.validate_url")
    async def test_process_url_calls_converter_and_ocr(
        self, mock_validate, mock_ocr, mock_converter, mock_uuid, tmp_path
    ):
        from app.config import settings
        from app.services.processor import process_url

        settings.upload_dir = str(tmp_path)
        mock_uuid.return_value.hex = "test123"
        mock_converter.url_to_pdf = AsyncMock(return_value=tmp_path / "test123.pdf")

        result, error, elapsed = await process_url("https://example.com", "json")

        assert error is None
        assert result is not None
        args, _ = mock_converter.url_to_pdf.await_args
        assert args[0] == "https://example.com"

    @patch("app.services.processor.uuid.uuid4")
    @patch("app.services.processor.converter")
    @patch("app.services.processor.ocr_service")
    @patch("app.services.processor.validate_url")
    async def test_process_url_markdown_format(
        self, mock_validate, mock_ocr, mock_converter, mock_uuid, tmp_path
    ):
        from app.config import settings
        from app.services.processor import process_url

        settings.upload_dir = str(tmp_path)
        mock_uuid.return_value.hex = "test456"
        mock_converter.url_to_pdf = AsyncMock(return_value=tmp_path / "test456.pdf")
        mock_ocr.to_markdown = MagicMock(return_value="# Hello")

        result, error, elapsed = await process_url("https://example.org", "markdown")

        assert error is None
        assert result == "# Hello"

    @patch("app.services.processor.uuid.uuid4")
    @patch("app.services.processor.converter")
    @patch("app.services.processor.ocr_service")
    @patch("app.services.processor.validate_url")
    async def test_process_url_xml_format(
        self, mock_validate, mock_ocr, mock_converter, mock_uuid, tmp_path
    ):
        from app.config import settings
        from app.services.processor import process_url

        settings.upload_dir = str(tmp_path)
        mock_uuid.return_value.hex = "test789"
        mock_converter.url_to_pdf = AsyncMock(return_value=tmp_path / "test789.pdf")
        mock_ocr.to_xml = MagicMock(return_value="<ocr></ocr>")

        result, error, elapsed = await process_url("https://example.net", "xml")

        assert error is None
        assert result == "<ocr></ocr>"

    @patch("app.services.processor.uuid.uuid4")
    @patch("app.services.processor.converter")
    @patch("app.services.processor.validate_url")
    async def test_process_url_converter_error(
        self, mock_validate, mock_converter, mock_uuid, tmp_path
    ):
        from app.config import settings
        from app.services.processor import process_url

        settings.upload_dir = str(tmp_path)
        mock_uuid.return_value.hex = "fail01"
        mock_converter.url_to_pdf = AsyncMock(
            side_effect=RuntimeError("Gotenberg down")
        )

        result, error, elapsed = await process_url("https://example.com", "json")

        assert result is None
        assert error == "Processing failed"

    @patch("app.services.processor.uuid.uuid4")
    @patch("app.services.processor.converter")
    @patch("app.services.processor.ocr_service")
    async def test_process_url_validation_error_caught(
        self, mock_ocr, mock_converter, mock_uuid, tmp_path
    ):
        from app.config import settings
        from app.services.processor import process_url

        settings.upload_dir = str(tmp_path)
        mock_uuid.return_value.hex = "valid01"
        mock_converter.url_to_pdf = AsyncMock(return_value=tmp_path / "valid01.pdf")

        result, error, elapsed = await process_url("file:///etc/passwd", "json")

        assert result is None
        assert "Only http/https" in error


class TestProcessHtml:
    @patch("app.services.processor.uuid.uuid4")
    @patch("app.services.processor.converter")
    @patch("app.services.processor.ocr_service")
    async def test_process_html_calls_converter_and_ocr(
        self, mock_ocr, mock_converter, mock_uuid, tmp_path
    ):
        from app.config import settings
        from app.services.processor import process_html

        settings.upload_dir = str(tmp_path)
        mock_uuid.return_value.hex = "html01"
        mock_converter.html_to_pdf = AsyncMock(return_value=tmp_path / "html01.pdf")

        files = [("index.html", b"<html></html>"), ("style.css", b"body {}")]
        result, error, elapsed = await process_html(files, "json")

        assert error is None
        assert result is not None
        mock_converter.html_to_pdf.assert_awaited_once()


class TestSplitGroupByHtml:
    @pytest.fixture(autouse=True)
    def _import(self):
        from app.routes.ocr import _split_group_by_html

        self._split = _split_group_by_html

    def test_single_html_becomes_one_group(self):
        entries = [("page1.html", b"<h1>A</h1>")]
        groups = self._split(entries)
        assert len(groups) == 1
        assert groups[0] == entries

    def test_two_html_files_become_two_groups(self):
        entries = [("a.html", b"<h1>A</h1>"), ("b.html", b"<h1>B</h1>")]
        groups = self._split(entries)
        assert len(groups) == 2
        assert len(groups[0]) == 1

    def test_html_with_asset_bound_to_preceding_html(self):
        entries = [
            ("a.html", b"<h1>A</h1>"),
            ("style.css", b"body {}"),
            ("b.html", b"<h1>B</h1>"),
        ]
        groups = self._split(entries)
        assert len(groups) == 2
        assert len(groups[0]) == 2  # a.html + style.css
        assert len(groups[1]) == 1  # b.html alone

    def test_assets_without_preceding_html_dropped(self):
        entries = [("style.css", b"body {}"), ("a.html", b"<h1>A</h1>")]
        groups = self._split(entries)
        assert len(groups) == 1  # style.css dropped
        assert groups[0][0][0] == "a.html"

    def test_empty_input(self):
        assert self._split([]) == []

    def test_non_html_only_dropped(self):
        entries = [("style.css", b"body {}")]
        assert self._split(entries) == []
