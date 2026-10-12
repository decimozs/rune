import pytest


def make_page(texts, scores, polys):
    return {"rec_texts": texts, "rec_scores": scores, "rec_polys": polys}


class TestStructure:
    def test_none_result(self, formatter):
        result = formatter.structure(None)
        assert result["pages"] == []

    def test_empty_list(self, formatter):
        result = formatter.structure([])
        assert result["pages"] == []

    @pytest.mark.parametrize(
        (
            "texts",
            "scores",
            "polys",
            "expected_count",
            "expected_text",
            "expected_conf",
        ),
        [
            (
                ["Hello"],
                [0.98],
                [[[10, 20], [100, 20], [100, 40], [10, 40]]],
                1,
                "Hello",
                0.98,
            ),
            (
                ["foo", "bar"],
                [0.9, 0.8],
                [
                    [[0, 0], [10, 0], [10, 10], [0, 10]],
                    [[20, 0], [30, 0], [30, 10], [20, 10]],
                ],
                2,
                "foo bar",
                0.9,
            ),
        ],
    )
    def test_words(
        self,
        formatter,
        texts,
        scores,
        polys,
        expected_count,
        expected_text,
        expected_conf,
    ):
        raw = [make_page(texts, scores, polys)]
        result = formatter.structure(raw)
        page = result["pages"][0]
        assert len(page["words"]) == expected_count
        assert page["extracted_text"] == expected_text
        assert page["words"][0]["confidence"] == expected_conf

    def test_multi_page(self, formatter):
        raw = [
            make_page(["pg1"], [0.9], [[[0, 0], [10, 0], [10, 10], [0, 10]]]),
            make_page(["pg2"], [0.95], [[[0, 0], [10, 0], [10, 10], [0, 10]]]),
        ]
        result = formatter.structure(raw)
        assert len(result["pages"]) == 2
        assert result["pages"][0]["page"] == 1
        assert result["pages"][1]["page"] == 2

    def test_texts_none_returns_empty_words(self, formatter):
        raw = [{"rec_texts": None, "rec_scores": None, "rec_polys": None}]
        result = formatter.structure(raw)
        assert len(result["pages"]) == 1
        assert result["pages"][0]["words"] == []

    def test_empty_texts_returns_empty_words(self, formatter):
        raw = [make_page([], [], [])]
        result = formatter.structure(raw)
        assert len(result["pages"][0]["words"]) == 0
