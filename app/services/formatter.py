import logging
from pathlib import Path
from typing import Any
from config import settings
from schemas.ocr import BoundingBox, WordBlock, OCRPage, OCRResult

logger = logging.getLogger(__name__)


class OCRFormatter:
    @staticmethod
    def structure(result: list[dict[str, Any]] | None, stem: str | None = None) -> dict[str, Any]:
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

            page_image_url = None
            ocr_width = None
            ocr_height = None
            if stem is not None:
                img = page.get("doc_preprocessor_res", {}).get("output_img")
                if img is not None:
                    h, w = img.shape[:2]
                    ocr_width = w
                    ocr_height = h
                    pages_dir = settings.output_dir_path / "pages" / stem
                    pages_dir.mkdir(parents=True, exist_ok=True)
                    img_path = pages_dir / f"page_{page_num}.png"
                    import cv2
                    cv2.imwrite(str(img_path), img)
                    page_image_url = f"/assets/pages/{stem}/page_{page_num}.png"

            pages.append(
                OCRPage(
                    page=page_num,
                    words=words,
                    extracted_text=" ".join(w.text for w in words),
                    page_image_url=page_image_url,
                    ocr_width=ocr_width,
                    ocr_height=ocr_height,
                )
            )

        return OCRResult(pages=pages).model_dump()
