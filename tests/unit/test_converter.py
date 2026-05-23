import pytest

from app.services.converter import converter, CONVERTIBLE_TYPES


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
