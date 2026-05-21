from fastapi import UploadFile
from services.engine import OCREngine, StructureEngine
from services.formatter import OCRFormatter
from services.markdown import MarkdownConverter
from services.exceptions import OCRValidationError, OCRRuntimeError


class OCRService:
    def __init__(self):
        self.engine = OCREngine()
        self.structure_engine = StructureEngine()
        self.formatter = OCRFormatter()
        self.markdown_converter = MarkdownConverter(self.structure_engine)

    async def init(self):
        await self.engine.init()

    def _validate_file(self, file: UploadFile) -> tuple[str, str]:
        if not file.filename:
            raise OCRValidationError("Uploaded file has no filename")
        if not file.content_type:
            raise OCRValidationError("Uploaded file has no content type")
        return file.filename, file.content_type

    def process(self, file_path: str, file: UploadFile):
        self._validate_file(file)
        result = self.engine.predict(file_path)
        return self.formatter.structure(result)

    def to_markdown(self, image_path: str, file: UploadFile) -> str:
        self._validate_file(file)
        result = self.structure_engine.predict(image_path)
        return self.markdown_converter.convert(result, image_path, file.filename, file.content_type)


ocr_service = OCRService()
