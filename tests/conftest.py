import pytest
from app.services.formatter import OCRFormatter


@pytest.fixture
def formatter():
    return OCRFormatter()
