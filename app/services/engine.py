import logging
from paddleocr import PaddleOCR, PPStructureV3
from config import settings

logger = logging.getLogger(__name__)


class OCREngine:
    def __init__(self):
        self.ocr_model = None

    @property
    def is_ready(self) -> bool:
        return self.ocr_model is not None

    async def init(self):
        self.ocr_model = PaddleOCR(
            use_textline_orientation=settings.use_textline_orientation,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
            ocr_version=settings.version,
        )

    async def shutdown(self):
        self.ocr_model = None
        logger.info("OCREngine released")

    def predict(self, file_path: str):
        if self.ocr_model is None:
            raise RuntimeError("OCREngine not initialized. Call init() first.")
        return self.ocr_model.predict(file_path)


class StructureEngine:
    def __init__(self):
        self._engine: PPStructureV3 | None = None

    @property
    def is_ready(self) -> bool:
        return self._engine is not None

    async def init(self):
        self._engine = PPStructureV3(
            use_textline_orientation=settings.use_textline_orientation,
            ocr_version=settings.version,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
        )

    async def shutdown(self):
        self._engine = None
        logger.info("StructureEngine released")

    def _get_engine(self) -> PPStructureV3:
        if self._engine is None:
            raise RuntimeError("StructureEngine not initialized. Call init() first.")
        return self._engine

    def predict(self, file_path: str):
        return self._get_engine().predict(file_path)

    def concatenate_pages(self, markdown_list):
        return self._get_engine().concatenate_markdown_pages(markdown_list)
