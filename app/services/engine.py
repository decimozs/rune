"""Wrappers around PaddleOCR and PPStructureV3 engines.

Both engines are initialized once at startup (not lazy) and never
re-created. They are NOT thread-safe — every call goes through
asyncio.to_thread in processor.py to avoid blocking the event loop.

PaddleOCR model loading takes ~22s on first run and ~300MB of RAM.

Protocols are defined here so consumers can depend on the interface
rather than concrete classes. Tests use FakeOCREngine and
FakeStructureEngine instead of patching import paths.
"""

import logging
import time
from typing import Protocol, runtime_checkable

from config import settings
from paddleocr import PaddleOCR, PPStructureV3

logger = logging.getLogger(__name__)


@runtime_checkable
class OCREngineProtocol(Protocol):
    """Interface: word-level OCR with bounding boxes."""

    @property
    def is_ready(self) -> bool: ...

    async def init(self) -> None: ...

    async def shutdown(self) -> None: ...

    def predict(self, file_path: str): ...


@runtime_checkable
class StructureEngineProtocol(Protocol):
    """Interface: structure-aware OCR (tables, layouts, markdown)."""

    @property
    def is_ready(self) -> bool: ...

    async def init(self) -> None: ...

    async def shutdown(self) -> None: ...

    def predict(self, file_path: str): ...

    def concatenate_pages(self, markdown_list: list): ...


class PaddleOCREngine:
    """Wraps PaddleOCR for text extraction with bounding boxes."""

    def __init__(self):
        self.ocr_model = None

    @property
    def is_ready(self) -> bool:
        return self.ocr_model is not None

    async def init(self):
        start = time.time()
        self.ocr_model = PaddleOCR(
            use_textline_orientation=settings.use_textline_orientation,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
            ocr_version=settings.version,
            use_doc_unwarping=False,
        )
        elapsed = round((time.time() - start) * 1000, 2)
        logger.info("OCREngine initialized in %sms", elapsed)

    async def shutdown(self):
        self.ocr_model = None
        logger.info("OCREngine released")

    def predict(self, file_path: str):
        if self.ocr_model is None:
            raise RuntimeError("OCREngine not initialized. Call init() first.")
        return self.ocr_model.predict(file_path)


class PaddleStructureEngine:
    """Wraps PPStructureV3 for structure-aware OCR (tables, layouts, markdown)."""

    def __init__(self):
        self._engine: PPStructureV3 | None = None

    @property
    def is_ready(self) -> bool:
        return self._engine is not None

    async def init(self):
        start = time.time()
        self._engine = PPStructureV3(
            use_textline_orientation=settings.use_textline_orientation,
            ocr_version=settings.version,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
        )
        elapsed = round((time.time() - start) * 1000, 2)
        logger.info("StructureEngine initialized in %sms", elapsed)

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
