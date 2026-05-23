from app.services.xml_formatter import to_xml


class TestToXml:
    def test_empty_pages(self):
        xml = to_xml({"pages": []})
        assert "ocrResult" in xml

    def test_single_word(self):
        data = {
            "pages": [
                {
                    "page": 1,
                    "words": [
                        {"text": "hello", "confidence": 0.98, "bbox": {"points": [[0, 0], [10, 0], [10, 10], [0, 10]]}}
                    ],
                    "extracted_text": "hello",
                }
            ]
        }
        xml = to_xml(data)
        assert "<page number=\"1\">" in xml
        assert "<text>hello</text>" in xml
        assert "0.98" in xml

    def test_multiple_words(self):
        data = {
            "pages": [
                {
                    "page": 1,
                    "words": [
                        {"text": "foo", "confidence": 0.9, "bbox": {"points": [[0, 0], [1, 0], [1, 1], [0, 1]]}},
                        {"text": "bar", "confidence": 0.8, "bbox": {"points": [[2, 0], [3, 0], [3, 1], [2, 1]]}},
                    ],
                    "extracted_text": "foo bar",
                }
            ]
        }
        xml = to_xml(data)
        assert xml.count("<word confidence") == 2

    def test_word_with_bbox_has_points(self):
        data = {
            "pages": [
                {
                    "page": 1,
                    "words": [
                        {"text": "hasbbox", "confidence": 0.9, "bbox": {"points": [[0, 0], [1, 0], [1, 1], [0, 1]]}},
                    ],
                    "extracted_text": "hasbbox",
                }
            ]
        }
        xml = to_xml(data)
        assert "<point" in xml
        assert xml.count("<point") == 4
