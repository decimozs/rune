"""Convert raw PaddleOCR output into structured Pydantic models.

PaddleOCR's predict() returns a list of dicts. Each page dict has:
    - rec_texts:  list[str]           — recognized text per word block
    - rec_scores: list[float]         — confidence per word block
    - rec_polys:  list[list[float]]   — 4-point bbox per word block
    - doc_preprocessor_res.output_img — numpy array of the rendered page
                                        (present only for PDF files)

This module maps those raw lists into typed Pydantic models
(WordBlock, OCRPage, OCRResult), optionally filtering fields
via JsonOutputOptions, and saves page images to disk for
serving via /assets/ static mount.
"""

import logging
from pathlib import Path
from typing import Any, Optional
from config import settings
from schemas.ocr import BoundingBox, WordBlock, OCRPage, OCRResult, JsonOutputOptions

logger = logging.getLogger(__name__)


class OCRFormatter:
    @staticmethod
    def structure(
        result: list[dict[str, Any]] | None,
        stem: str | None = None,
        options: Optional[JsonOutputOptions] = None,
    ) -> dict[str, Any]:
        """Convert PaddleOCR page list into a structured OCRResult dict.

        Args:
            result: Raw PaddleOCR output (list of page dicts).
            stem: Unique directory name for saving page images.
            options: Controls which fields appear in JSON output.

        Returns:
            Serialized OCRResult dict (exclude_none=True strips nulls).
        """
        if not result or result[0] is None:
            logger.warning("OCR returned empty result")
            return OCRResult(pages=[]).model_dump(exclude_none=True)

        pages = []
        for page_num, page in enumerate(result, start=1):
            texts = page.get("rec_texts", []) or []
            scores = page.get("rec_scores", []) or []
            boxes = page.get("rec_polys", []) or []

            words = []
            for text, score, box in zip(texts, scores, boxes):
                bbox = BoundingBox(
                    points=box.tolist() if hasattr(box, "tolist") else box
                ) if options is None or options.include_bbox else None

                words.append(
                    WordBlock(
                        text=text,
                        confidence=round(float(score), 4) if options is None or options.include_confidence else None,
                        bbox=bbox,
                    )
                )

            page_image_url = None
            ocr_width = None
            ocr_height = None
            save_page_image = options is None or options.include_page_image
            if stem is not None and save_page_image:
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

            extracted_text = None
            if options is None or options.include_extracted_text:
                extracted_text = " ".join(w.text for w in words)

            pages.append(
                OCRPage(
                    page=page_num,
                    words=words,
                    extracted_text=extracted_text,
                    page_image_url=page_image_url,
                    ocr_width=ocr_width,
                    ocr_height=ocr_height,
                )
            )

        return OCRResult(pages=pages).model_dump(exclude_none=True)
