from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional


class ResponseMetadata(BaseModel):
    timestamp: datetime
    model: str
    format: str
    processing_time_ms: Optional[float] = None
    file_name: str
    file_type: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse(BaseModel):
    success: bool
    metadata: Optional[ResponseMetadata] = None
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
