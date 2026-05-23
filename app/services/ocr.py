import logging
import uuid
from services.engine import OCREngine, StructureEngine
from services.formatter import OCRFormatter
from services.markdown import MarkdownConverter
from services.xml_formatter import to_xml as format_xml

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        self.engine = OCREngine()
        self.structure_engine = StructureEngine()
        self.formatter = OCRFormatter()
        self.markdown_converter = MarkdownConverter(self.structure_engine)

    @property
    def is_ready(self) -> bool:
        return self.engine.is_ready and self.structure_engine.is_ready

    async def init(self):
        await self.engine.init()
        await self.structure_engine.init()

    async def shutdown(self):
        await self.structure_engine.shutdown()
        await self.engine.shutdown()

    def process(self, file_path: str, filename: str, content_type: str) -> dict:
        stem = uuid.uuid4().hex
        result = self.engine.predict(file_path)
        return self.formatter.structure(result, stem=stem)

    def to_markdown(
        self,
        file_path: str,
        filename: str,
        content_type: str,
    ) -> str:
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
        result = self.engine.predict(file_path)
        raw = self.formatter.structure(result)
        return format_xml(raw)


ocr_service = OCRService()
