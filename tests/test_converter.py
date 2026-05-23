from app.services.converter import converter, CONVERTIBLE_TYPES


class TestConvertibleTypes:
    def test_doc_is_convertible(self):
        assert "application/msword" in CONVERTIBLE_TYPES

    def test_docx_is_convertible(self):
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in CONVERTIBLE_TYPES

    def test_pdf_is_not_convertible(self):
        assert "application/pdf" not in CONVERTIBLE_TYPES

    def test_png_is_not_convertible(self):
        assert "image/png" not in CONVERTIBLE_TYPES


class TestNeedsConversion:
    def test_office_doc_returns_true(self):
        assert converter.needs_conversion("application/msword") is True

    def test_pdf_returns_false(self):
        assert converter.needs_conversion("application/pdf") is False

    def test_image_returns_false(self):
        assert converter.needs_conversion("image/jpeg") is False

    def test_unknown_returns_false(self):
        assert converter.needs_conversion("application/zip") is False
