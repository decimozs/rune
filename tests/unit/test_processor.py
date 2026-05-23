import pytest

from app.services.processor import TEXT_BASED_TYPES, _ocr_semaphore


class TestTextBasedTypes:
    @pytest.mark.parametrize(
        "mime,expected",
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
