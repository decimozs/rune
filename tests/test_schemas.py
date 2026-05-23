import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.schemas.ocr import BoundingBox, WordBlock, OCRPage, OCRResult
from app.schemas.response import APIResponse, ResponseMetadata, ErrorDetail


class TestBoundingBox:
    def test_valid_points(self):
        b = BoundingBox(points=[[0, 0], [10, 0], [10, 10], [0, 10]])
        assert len(b.points) == 4

    def test_less_than_four_points_raises(self):
        with pytest.raises(ValidationError):
            BoundingBox(points=[[0, 0], [10, 0], [10, 10]])

    def test_more_than_four_points_raises(self):
        with pytest.raises(ValidationError):
            BoundingBox(points=[[0, 0], [1, 0], [1, 1], [0, 1], [2, 2]])


class TestWordBlock:
    def test_minimal(self):
        w = WordBlock(text="hello", confidence=0.95, bbox={"points": [[0, 0], [10, 0], [10, 10], [0, 10]]})
        assert w.text == "hello"
        assert w.confidence == 0.95

    def test_confidence_any_float(self):
        w = WordBlock(text="x", confidence=1.5, bbox={"points": [[0, 0], [1, 0], [1, 1], [0, 1]]})
        assert w.confidence == 1.5


class TestOCRPage:
    def test_optional_fields_default_to_none(self):
        p = OCRPage(page=1, words=[], extracted_text="")
        assert p.page_image_url is None
        assert p.ocr_width is None
        assert p.ocr_height is None


class TestOCRResult:
    def test_empty_pages(self):
        r = OCRResult(pages=[])
        assert r.pages == []

    def test_single_page(self):
        page = OCRPage(page=1, words=[], extracted_text="")
        r = OCRResult(pages=[page])
        assert r.pages[0].page == 1


class TestAPIResponse:
    def test_success_envelope(self):
        ts = datetime.now(timezone.utc)
        r = APIResponse(
            success=True,
            metadata=ResponseMetadata(timestamp=ts, model="test", format="json"),
            data={"key": "val"},
        )
        d = r.model_dump(exclude_none=True)
        assert d["success"] is True
        assert d["data"]["key"] == "val"

    def test_error_envelope(self):
        r = APIResponse(
            success=False,
            error=ErrorDetail(code="TEST_ERR", message="something broke"),
        )
        d = r.model_dump(exclude_none=True)
        assert d["success"] is False
        assert d["error"]["code"] == "TEST_ERR"
