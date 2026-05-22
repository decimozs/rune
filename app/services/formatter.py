import logging
from schemas.ocr import BoundingBox, WordBlock, OCRPage, OCRResult

logger = logging.getLogger(__name__)


class OCRFormatter:
    @staticmethod
    def structure(result) -> dict:
        if not result or result[0] is None:
            logger.warning("OCR returned empty result")
            return OCRResult(pages=[]).model_dump()

        pages = []
        for page_num, page in enumerate(result, start=1):
            texts = page.get("rec_texts", []) or []
            scores = page.get("rec_scores", []) or []
            boxes = page.get("rec_polys", []) or []

            words = []
            for text, score, box in zip(texts, scores, boxes):
                words.append(
                    WordBlock(
                        text=text,
                        confidence=round(float(score), 4),
                        bbox=BoundingBox(
                            points=box.tolist() if hasattr(box, "tolist") else box
                        ),
                    )
                )

            pages.append(
                OCRPage(
                    page=page_num,
                    words=words,
                    extracted_text=" ".join(w.text for w in words),
                )
            )

        return OCRResult(pages=pages).model_dump()
