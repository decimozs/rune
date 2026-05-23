from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest

from app.services.converter import converter, DocumentConverter, CONVERTIBLE_TYPES


class TestConvertibleTypes:
    @pytest.mark.parametrize(
        "mime,expected",
        [
            ("application/msword", True),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
            ("application/pdf", False),
            ("image/png", False),
            ("image/jpeg", False),
            ("text/csv", True),
            ("text/rtf", True),
            ("application/zip", False),
        ],
    )
    def test_convertible_types(self, mime, expected):
        assert (mime in CONVERTIBLE_TYPES) == expected


class TestNeedsConversion:
    @pytest.mark.parametrize(
        "mime,expected",
        [
            ("application/msword", True),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
            ("application/pdf", False),
            ("image/jpeg", False),
            ("application/zip", False),
        ],
    )
    def test_needs_conversion(self, mime, expected):
        assert converter.needs_conversion(mime) is expected


class TestChromiumUrl:
    async def test_url_to_pdf_sends_correct_request(self, tmp_path):
        c = DocumentConverter()
        c._client = AsyncMock()
        c._client.post = AsyncMock()
        c._client.post.return_value = MagicMock(status_code=200, content=b"pdf-data")

        out = tmp_path / "result.pdf"

        result = await c.url_to_pdf("https://example.com", out)

        assert result == out
        assert out.read_bytes() == b"pdf-data"
        call_kwargs = c._client.post.call_args.kwargs
        assert str(c._client.post.call_args.args[0]).endswith("/forms/chromium/convert/url")
        assert call_kwargs["data"]["url"] == "https://example.com"


class TestChromiumHtml:
    async def test_html_to_pdf_sends_files(self, tmp_path):
        c = DocumentConverter()
        c._client = AsyncMock()
        c._client.post = AsyncMock()
        c._client.post.return_value = MagicMock(status_code=200, content=b"pdf-data")

        out = tmp_path / "result.pdf"
        files = {"index.html": b"<html></html>", "style.css": b"body {}"}

        result = await c.html_to_pdf(files, out)

        assert result == out
        assert out.read_bytes() == b"pdf-data"
        call_kwargs = c._client.post.call_args.kwargs
        assert str(c._client.post.call_args.args[0]).endswith("/forms/chromium/convert/html")
        req_files = call_kwargs["files"]
        field_map = {f[1][0]: f[0] for f in req_files}
        assert field_map["index.html"] == "index.html"
        assert field_map["style.css"] == "files"

    async def test_html_to_pdf_renames_any_html_to_index_html(self, tmp_path):
        c = DocumentConverter()
        c._client = AsyncMock()
        c._client.post = AsyncMock()
        c._client.post.return_value = MagicMock(status_code=200, content=b"pdf-data")

        out = tmp_path / "result.pdf"
        files = {"page.html": b"<html></html>"}

        await c.html_to_pdf(files, out)

        call_kwargs = c._client.post.call_args.kwargs
        req_files = call_kwargs["files"]
        sent_name = req_files[0][1][0]
        assert sent_name == "index.html"
        assert req_files[0][0] == "index.html"


class TestChromiumEdgeCases:
    async def test_url_to_pdf_encodes_special_chars(self, tmp_path):
        c = DocumentConverter()
        c._client = AsyncMock()
        c._client.post = AsyncMock()
        c._client.post.return_value = MagicMock(status_code=200, content=b"")

        out = tmp_path / "r.pdf"
        await c.url_to_pdf("https://example.com/path?a=b&c=d", out)

        call_data = c._client.post.call_args.kwargs["data"]
        assert call_data["url"] == "https://example.com/path?a=b&c=d"

    async def test_html_to_pdf_empty_files(self, tmp_path):
        c = DocumentConverter()
        c._client = AsyncMock()
        c._client.post = AsyncMock()
        c._client.post.return_value = MagicMock(status_code=200, content=b"")

        out = tmp_path / "r.pdf"
        await c.html_to_pdf({}, out)

        assert c._client.post.awaited
