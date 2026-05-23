import pytest
from app.services.processor import TEXT_BASED_TYPES, _ocr_semaphore


class TestTextBasedTypes:
    def test_csv_included(self):
        assert "text/csv" in TEXT_BASED_TYPES

    def test_rtf_included(self):
        assert "text/rtf" in TEXT_BASED_TYPES

    def test_pdf_not_included(self):
        assert "application/pdf" not in TEXT_BASED_TYPES


class TestSemaphore:
    def test_semaphore_value_from_config(self):
        from app.config import settings
        assert _ocr_semaphore._value == settings.max_concurrent_jobs
        assert _ocr_semaphore._value >= 1
