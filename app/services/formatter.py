import logging

logger = logging.getLogger(__name__)


class OCRFormatter:
    @staticmethod
    def structure(result):
        structured = {
            "pages": [],
        }

        if not result or result[0] is None:
            logger.warning("OCR returned empty result for file")
            return structured

        for page_num, page in enumerate(result, start=1):
            texts = page.get("rec_texts", []) or []
            scores = page.get("rec_scores", []) or []
            boxes = page.get("rec_polys", []) or []

            words = []

            for text, score, box in zip(texts, scores, boxes):
                words.append(
                    {
                        "text": text,
                        "confidence": round(float(score), 4),
                        "bbox": {
                            "points": box.tolist() if hasattr(box, "tolist") else box
                        },
                    }
                )

            structured["pages"].append(
                {
                    "page": page_num,
                    "words": words,
                    "extracted_text": " ".join(w["text"] for w in words),
                }
            )

        return structured
