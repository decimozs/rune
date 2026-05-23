import pytest

from app.services.xml_formatter import to_xml


def make_page_data(page_num, words):
    texts = " ".join(w[0] for w in words)
    return {
        "page": page_num,
        "words": [
            {"text": w[0], "confidence": w[1], "bbox": {"points": w[2]}}
            for w in words
        ],
        "extracted_text": texts,
    }


class TestToXml:
    def test_empty_pages(self):
        xml = to_xml({"pages": []})
        assert "ocrResult" in xml

    @pytest.mark.parametrize(
        "words,expected_word_count,expected_points",
        [
            (
                [("hello", 0.98, [[0, 0], [10, 0], [10, 10], [0, 10]])],
                1,
                False,
            ),
            (
                [
                    ("foo", 0.9, [[0, 0], [1, 0], [1, 1], [0, 1]]),
                    ("bar", 0.8, [[2, 0], [3, 0], [3, 1], [2, 1]]),
                ],
                2,
                False,
            ),
        ],
    )
    def test_xml_word_count(self, words, expected_word_count, expected_points):
        data = make_page_data(1, words)
        xml = to_xml({"pages": [data]})
        assert xml.count("<word confidence") == expected_word_count

    def test_word_with_bbox_has_points(self):
        data = make_page_data(1, [("hasbbox", 0.9, [[0, 0], [1, 0], [1, 1], [0, 1]])])
        xml = to_xml({"pages": [data]})
        assert "<point" in xml
        assert xml.count("<point") == 4

    def test_page_number_in_xml(self):
        data = make_page_data(1, [("hello", 0.98, [[0, 0], [10, 0], [10, 10], [0, 10]])])
        xml = to_xml({"pages": [data]})
        assert '<page number="1">' in xml
