from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional


class ResponseMetadata(BaseModel):
    timestamp: datetime
    model: str
    format: str
    processing_time_ms: Optional[float] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse(BaseModel):
    success: bool
    metadata: Optional[ResponseMetadata] = None
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
