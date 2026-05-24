"""Wrappers around PaddleOCR and PPStructureV3 engines.

Both engines are initialized once at startup (not lazy) and never
re-created. They are NOT thread-safe — every call goes through
asyncio.to_thread in processor.py to avoid blocking the event loop.

PaddleOCR model loading takes ~22s on first run and ~300MB of RAM.
"""

import logging
from paddleocr import PaddleOCR, PPStructureV3
from config import settings

logger = logging.getLogger(__name__)


class OCREngine:
    """Wraps PaddleOCR for text extraction with bounding boxes."""

    def __init__(self):
        self.ocr_model = None

    @property
    def is_ready(self) -> bool:
        return self.ocr_model is not None

    async def init(self):
        """Initialize the PaddleOCR model. Called once in main.py lifespan."""
        self.ocr_model = PaddleOCR(
            use_textline_orientation=settings.use_textline_orientation,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
            ocr_version=settings.version,
            use_doc_unwarping=False,
        )

    async def shutdown(self):
        """Release the model. Called during graceful shutdown."""
        self.ocr_model = None
        logger.info("OCREngine released")

    def predict(self, file_path: str):
        """Run OCR on a single file. SYNCHRONOUS — caller must use to_thread."""
        if self.ocr_model is None:
            raise RuntimeError("OCREngine not initialized. Call init() first.")
        return self.ocr_model.predict(file_path)


class StructureEngine:
    """Wraps PPStructureV3 for structure-aware OCR (tables, layouts, markdown)."""

    def __init__(self):
        self._engine: PPStructureV3 | None = None

    @property
    def is_ready(self) -> bool:
        return self._engine is not None

    async def init(self):
        """Initialize the PPStructureV3 model. Called once in main.py lifespan."""
        self._engine = PPStructureV3(
            use_textline_orientation=settings.use_textline_orientation,
            ocr_version=settings.version,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
        )

    async def shutdown(self):
        """Release the model. Called during graceful shutdown."""
        self._engine = None
        logger.info("StructureEngine released")

    def _get_engine(self) -> PPStructureV3:
        if self._engine is None:
            raise RuntimeError("StructureEngine not initialized. Call init() first.")
        return self._engine

    def predict(self, file_path: str):
        """Run structure analysis. SYNCHRONOUS — caller must use to_thread."""
        return self._get_engine().predict(file_path)

    def concatenate_pages(self, markdown_list):
        """Merge per-page markdown into a single document using PaddleOCR's built-in method."""
        return self._get_engine().concatenate_markdown_pages(markdown_list)
