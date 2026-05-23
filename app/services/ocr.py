import logging
from services.engine import OCREngine, StructureEngine
from services.formatter import OCRFormatter
from services.markdown import MarkdownConverter

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

    def process(self, file_path: str, filename: str, content_type: str) -> dict:
        result = self.engine.predict(file_path)
        return self.formatter.structure(result)

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


ocr_service = OCRService()
