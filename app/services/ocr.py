from fastapi import UploadFile
from services.engine import OCREngine, StructureEngine
from services.formatter import OCRFormatter
from services.markdown import MarkdownConverter


class OCRService:
    def __init__(self):
        self.engine = OCREngine()
        self.structure_engine = StructureEngine()
        self.formatter = OCRFormatter()
        self.markdown_converter = MarkdownConverter(self.structure_engine)

    async def init(self):
        await self.engine.init()

    def process(self, file_path: str, file: UploadFile):
        result = self.engine.predict(file_path)
        return self.formatter.structure(
            result, file_path, file.filename, file.content_type
        )

    def to_markdown(self, image_path: str, file: UploadFile) -> str:
        result = self.structure_engine.predict(image_path)
        return self.markdown_converter.convert(
            result, image_path, file.filename, file.content_type
        )


ocr_service = OCRService()
