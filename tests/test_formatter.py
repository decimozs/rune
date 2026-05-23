from app.services.formatter import OCRFormatter

formatter = OCRFormatter()

# PaddleOCR raw output shape: list[dict] with keys rec_texts, rec_scores, rec_polys
# rec_polys values are ndarray-like with .tolist() method; here we use plain lists


def make_page(texts, scores, polys):
    return {"rec_texts": texts, "rec_scores": scores, "rec_polys": polys}


class TestStructure:
    def test_none_result(self):
        result = formatter.structure(None)
        assert result["pages"] == []

    def test_empty_list(self):
        result = formatter.structure([])
        assert result["pages"] == []

    def test_single_word(self):
        raw = [make_page(["Hello"], [0.98], [[[10, 20], [100, 20], [100, 40], [10, 40]]])]
        result = formatter.structure(raw)
        assert len(result["pages"]) == 1
        page = result["pages"][0]
        assert page["page"] == 1
        assert len(page["words"]) == 1
        assert page["words"][0]["text"] == "Hello"
        assert page["words"][0]["confidence"] == 0.98
        assert page["extracted_text"] == "Hello"

    def test_multiple_words(self):
        raw = [make_page(
            ["foo", "bar"],
            [0.9, 0.8],
            [[[0, 0], [10, 0], [10, 10], [0, 10]], [[20, 0], [30, 0], [30, 10], [20, 10]]]
        )]
        result = formatter.structure(raw)
        assert len(result["pages"][0]["words"]) == 2
        assert result["pages"][0]["extracted_text"] == "foo bar"

    def test_multi_page(self):
        raw = [
            make_page(["pg1"], [0.9], [[[0, 0], [10, 0], [10, 10], [0, 10]]]),
            make_page(["pg2"], [0.95], [[[0, 0], [10, 0], [10, 10], [0, 10]]]),
        ]
        result = formatter.structure(raw)
        assert len(result["pages"]) == 2
        assert result["pages"][0]["page"] == 1
        assert result["pages"][1]["page"] == 2

    def test_texts_none_returns_empty_words(self):
        raw = [{"rec_texts": None, "rec_scores": None, "rec_polys": None}]
        result = formatter.structure(raw)
        assert len(result["pages"]) == 1
        assert result["pages"][0]["words"] == []

    def test_empty_texts_returns_empty_words(self):
        raw = [make_page([], [], [])]
        result = formatter.structure(raw)
        assert len(result["pages"][0]["words"]) == 0
