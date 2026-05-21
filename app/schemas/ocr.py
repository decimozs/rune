from pydantic import BaseModel


class WordBlock(BaseModel):
    text: str
    confidence: float
    bbox: list


class OCRPage(BaseModel):
    page: int
    words: list[WordBlock]
    extracted_text: str


class OCRResponse(BaseModel):
    file: str
    path: str
    type: str
    pages: list[OCRPage]
