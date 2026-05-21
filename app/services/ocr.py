from fastapi import File, UploadFile
from paddleocr import PaddleOCR


class OCRService:
    def __init__(self):
        self.model = None

    async def init(self):
        self.model = PaddleOCR(
            use_textline_orientation=True,
            lang="en",
            enable_mkldnn=False,
            ocr_version="PP-OCRv4",
        )

    def process(self, file_path: str, file: UploadFile = File(...)):
        if self.model is None:
            raise RuntimeError("OCRService is not initialized. Call init() first.")

        result = self.model.predict(file_path)
        return self._structure(
            result,
            file_path,
            file,
        )

    def _structure(self, result, image_path: str, file: UploadFile = File(...)):
        structured = {
            "file": file.filename,
            "path": image_path,
            "type": file.content_type,
            "pages": [],
        }

        if not result or result[0] is None:
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
                        "bbox": box.tolist() if hasattr(box, "tolist") else box,
                    }
                )

            structured["pages"].append(
                {
                    "page": page_num,
                    "words": words,
                    "extracted_text": " ".join(w["text"] for w in words),
                }
            )

        print(structured)
        return structured


ocr_service = OCRService()
