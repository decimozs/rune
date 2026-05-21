from paddleocr import PaddleOCR, PPStructureV3


class OCREngine:
    def __init__(self):
        self.ocr_model = None

    async def init(self):
        self.ocr_model = PaddleOCR(
            use_textline_orientation=True,
            lang="en",
            enable_mkldnn=False,
            ocr_version="PP-OCRv4",
        )

    def predict(self, file_path: str):
        if self.ocr_model is None:
            raise RuntimeError("OCREngine not initialized. Call init() first.")
        return self.ocr_model.predict(file_path)


class StructureEngine:
    def predict(self, file_path: str):
        engine = PPStructureV3(
            use_textline_orientation=True,
            ocr_version="PP-OCRv4",
            lang="en",
            enable_mkldnn=False,
        )
        return engine.predict(file_path)

    def concatenate_pages(self, markdown_list):
        engine = PPStructureV3(
            use_textline_orientation=True,
            ocr_version="PP-OCRv4",
            lang="en",
            enable_mkldnn=False,
        )
        return engine.concatenate_markdown_pages(markdown_list)
