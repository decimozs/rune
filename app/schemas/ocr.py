"""Pydantic models for OCR input options, output structure, and API responses.

BoundingBox enforces exactly 4 corner points. JsonOutputOptions controls
field visibility in JSON output. BatchStatus and SingleJobStatus model
the async job API responses.
"""

from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Any, Optional


class BoundingBox(BaseModel):
    """Quadrilateral bounding box with exactly 4 [x, y] points.

    Order typically follows: top-left, top-right, bottom-right, bottom-left.
    """
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
    """Controls which fields appear in JSON output. Only affects JSON format.

    Setting any to False strips the field from the response entirely
    (not set to null), via exclude_none=True in the final model dump.
    """
    include_bbox: bool = True
    include_confidence: bool = True
    include_extracted_text: bool = True
    include_page_image: bool = True


class WordBlock(BaseModel):
    """A single recognized word with optional bounding box and confidence."""
    text: str
    confidence: Optional[float] = None
    bbox: Optional[BoundingBox] = None


class OCRPage(BaseModel):
    """One page of OCR results. page_image_url links to the rendered page image."""
    page: int
    words: list[WordBlock]
    extracted_text: Optional[str] = None
    page_image_url: Optional[str] = None
    ocr_width: Optional[int] = None
    ocr_height: Optional[int] = None


class OCRResult(BaseModel):
    """Complete OCR result across all pages."""
    pages: list[OCRPage]


class BatchItemResult(BaseModel):
    """Result for one file in a batch. success=False if processing failed."""
    file_name: str
    file_type: str
    processing_time_ms: float
    success: bool
    data: Optional[Any] = None
    error: Optional[dict] = None


class BatchStatus(BaseModel):
    """Response model for GET /parse/batch/{id}."""
    batch_id: str
    status: str
    total_files: int
    completed: int
    failed: int
    processing_time_ms: Optional[float] = None
    items: list[Optional[BatchItemResult]]
    created_at: datetime


class SingleJobStatus(BaseModel):
    """Response model for GET /parse/jobs/{id}."""
    job_id: str
    status: str
    file_name: str
    file_type: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    data: Optional[Any] = None
    error: Optional[dict] = None
