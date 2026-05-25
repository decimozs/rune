"""Top-level OCR service facade.

Composes an OCREngine, StructureEngine, OCRFormatter,
MarkdownConverter, and XML formatter into a unified interface.
The module-level ocr_service singleton is imported by routes and
processors. Engines are injected via constructor (uses PaddleOCR
concretions by default).

Each output format uses a different engine:
    - JSON/XML:        OCREngine (PaddleOCR) + OCRFormatter
    - Markdown output: StructureEngine (PPStructureV3) + MarkdownConverter

All predict() calls are synchronous and CPU-bound. The caller in
processor.py wraps them in asyncio.to_thread.
"""

import logging
import uuid

from schemas.ocr import JsonOutputOptions
from services.engine import (
    OCREngineProtocol,
    PaddleOCREngine,
    PaddleStructureEngine,
    StructureEngineProtocol,
)
from services.formatter import OCRFormatter
from services.markdown import MarkdownConverter
from services.xml_formatter import to_xml as format_xml

logger = logging.getLogger(__name__)


class OCRService:
    """Orchestrates OCR engines and formatters.

    Engines are injected via constructor so callers can substitute
    test doubles. init() loads models (slow). predict methods are
    synchronous — wrap in to_thread.
    """

    def __init__(
        self,
        engine: OCREngineProtocol | None = None,
        struct_engine: StructureEngineProtocol | None = None,
    ):
        self.engine = engine or PaddleOCREngine()
        self.structure_engine = struct_engine or PaddleStructureEngine()
        self.formatter = OCRFormatter()
        self.markdown_converter = MarkdownConverter(self.structure_engine)

    @property
    def is_ready(self) -> bool:
        """True once both PaddleOCR and PPStructureV3 models are loaded."""
        return self.engine.is_ready and self.structure_engine.is_ready

    async def init(self):
        """Load both models. Called once in main.py lifespan. Blocks ~30s."""
        await self.engine.init()
        await self.structure_engine.init()

    async def shutdown(self):
        """Release both models. Called during graceful shutdown."""
        await self.structure_engine.shutdown()
        await self.engine.shutdown()

    def process(
        self,
        file_path: str,
        filename: str,
        content_type: str,
        options: JsonOutputOptions | None = None,
    ) -> dict:
        """OCR with PaddleOCR → structured dict for JSON output.

        Page images are saved to pages/{stem}/page_{N}.png in the
        shared ocr_assets volume and served by nginx. The stem is a
        random UUID to avoid collisions.
        """
        stem = uuid.uuid4().hex
        result = self.engine.predict(file_path)
        return self.formatter.structure(result, stem=stem, options=options)

    def to_markdown(
        self,
        file_path: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Structure-aware OCR → markdown string.

        Uses PPStructureV3 which understands tables, headings, and
        basic document layout. Slower than plain OCR but produces
        richer output.
        """
        result = self.structure_engine.predict(file_path)
        return self.markdown_converter.convert(
            result,
            file_path,
            filename,
            content_type,
        )

    def to_xml(
        self,
        file_path: str,
        filename: str,
        content_type: str,
    ) -> str:
        """OCR → XML string using stdlib xml.etree.ElementTree."""
        result = self.engine.predict(file_path)
        raw = self.formatter.structure(result)
        return format_xml(raw)


ocr_service = OCRService()
