from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Any, Optional


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


class JsonOutputOptions(BaseModel):
    include_bbox: bool = True
    include_confidence: bool = True
    include_extracted_text: bool = True
    include_page_image: bool = True


class WordBlock(BaseModel):
    text: str
    confidence: Optional[float] = None
    bbox: Optional[BoundingBox] = None


class OCRPage(BaseModel):
    page: int
    words: list[WordBlock]
    extracted_text: Optional[str] = None
    page_image_url: Optional[str] = None
    ocr_width: Optional[int] = None
    ocr_height: Optional[int] = None


class OCRResult(BaseModel):
    pages: list[OCRPage]


class BatchItemResult(BaseModel):
    file_name: str
    file_type: str
    processing_time_ms: float
    success: bool
    data: Optional[Any] = None
    error: Optional[dict] = None


class BatchStatus(BaseModel):
    batch_id: str
    status: str
    total_files: int
    completed: int
    failed: int
    processing_time_ms: Optional[float] = None
    items: list[Optional[BatchItemResult]]
    created_at: datetime


class SingleJobStatus(BaseModel):
    job_id: str
    status: str
    file_name: str
    file_type: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    data: Optional[Any] = None
    error: Optional[dict] = None
