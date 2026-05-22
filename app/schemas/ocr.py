from pydantic import BaseModel, field_validator


class BoundingBox(BaseModel):
    points: list[list[float]]

    @field_validator("points")
    @classmethod
    def validate_quad(cls, v):
        if len(v) != 4:
            raise ValueError("Bounding box must have exactly 4 points")
        for point in v:
            if len(point) != 2:
                raise ValueError("Each point must have [x, y] coordinates")
        return v


class WordBlock(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBox


class OCRPage(BaseModel):
    page: int
    words: list[WordBlock]
    extracted_text: str


class OCRResult(BaseModel):
    pages: list[OCRPage]
