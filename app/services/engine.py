"""Wrappers around PaddleOCR and PPStructureV3 engines.

Both engines support multiple model versions loaded simultaneously.
Models are keyed by version string (e.g. "PP-OCRv4", "PP-OCRv5") and
initialized on first use (lazy) unless pre-loaded at startup.

Engines are NOT thread-safe — every call goes through
asyncio.to_thread in processor.py to avoid blocking the event loop.

PaddleOCR model loading takes ~22s per version on first run and
~300MB of RAM per version.

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

    def predict(self, file_path: str, version: str | None = None): ...


@runtime_checkable
class StructureEngineProtocol(Protocol):
    """Interface: structure-aware OCR (tables, layouts, markdown)."""

    @property
    def is_ready(self) -> bool: ...

    async def init(self) -> None: ...

    async def shutdown(self) -> None: ...

    def predict(self, file_path: str, version: str | None = None): ...

    def concatenate_pages(self, markdown_list: list): ...


class PaddleOCREngine:
    """Wraps PaddleOCR for text extraction with bounding boxes.

    Supports multiple model versions. Versions listed in
    ``settings.models_list`` are pre-loaded at startup. Others are
    lazy-loaded on first call to ``predict()`` with that version.
    """

    def __init__(self):
        self._models: dict[str, PaddleOCR] = {}
        self._default_version: str = settings.version

    @property
    def is_ready(self) -> bool:
        return bool(self._models)

    async def init(self):
        """Pre-load all configured model versions."""
        for ver in settings.models_list:
            if ver not in self._models:
                self._load(ver)
        if self._default_version not in self._models:
            self._load(self._default_version)

    async def shutdown(self):
        self._models.clear()
        logger.info("OCREngine released")

    def _load(self, version: str):
        start = time.time()
        self._models[version] = PaddleOCR(
            use_textline_orientation=settings.use_textline_orientation,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
            ocr_version=version,
            use_doc_unwarping=False,
        )
        elapsed = round((time.time() - start) * 1000, 2)
        logger.info("OCREngine[%s] initialized in %sms", version, elapsed)

    def _get_model(self, version: str | None = None) -> PaddleOCR:
        ver = version or self._default_version
        if ver not in self._models:
            self._load(ver)
        return self._models[ver]

    def predict(self, file_path: str, version: str | None = None):
        model = self._get_model(version)
        return model.predict(file_path)


class PaddleStructureEngine:
    """Wraps PPStructureV3 for structure-aware OCR (tables, layouts, markdown).

    Supports multiple model versions. Versions listed in
    ``settings.models_list`` are pre-loaded at startup. Others are
    lazy-loaded on first call to ``predict()`` with that version.
    """

    def __init__(self):
        self._engines: dict[str, PPStructureV3] = {}
        self._default_version: str = settings.version

    @property
    def is_ready(self) -> bool:
        return bool(self._engines)

    async def init(self):
        """Pre-load all configured model versions."""
        for ver in settings.models_list:
            if ver not in self._engines:
                self._load(ver)
        if self._default_version not in self._engines:
            self._load(self._default_version)

    async def shutdown(self):
        self._engines.clear()
        logger.info("StructureEngine released")

    def _load(self, version: str):
        start = time.time()
        self._engines[version] = PPStructureV3(
            use_textline_orientation=settings.use_textline_orientation,
            ocr_version=version,
            lang=settings.lang,
            enable_mkldnn=settings.enable_mkldnn,
        )
        elapsed = round((time.time() - start) * 1000, 2)
        logger.info("StructureEngine[%s] initialized in %sms", version, elapsed)

    def _get_engine(self, version: str | None = None) -> PPStructureV3:
        ver = version or self._default_version
        if ver not in self._engines:
            self._load(ver)
        return self._engines[ver]

    def predict(self, file_path: str, version: str | None = None):
        return self._get_engine(version).predict(file_path)

    def concatenate_pages(self, markdown_list):
        return self._get_engine().concatenate_markdown_pages(markdown_list)
