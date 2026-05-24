"""Unified API response envelope used by every endpoint.

All endpoints wrap their response in APIResponse so clients always
get a predictable shape regardless of success or failure.

Optional fields in ResponseMetadata are absent for batch and background
creation endpoints where processing hasn't started yet.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional


class ResponseMetadata(BaseModel):
    """Timing, model info, and file details attached to every response."""
    timestamp: datetime
    model: str
    format: str
    processing_time_ms: Optional[float] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None


class ErrorDetail(BaseModel):
    """Structured error code and message returned on failure."""
    code: str
    message: str


class APIResponse(BaseModel):
    """Top-level response envelope wrapping data or error.

    On success: {success: true, metadata: {...}, data: ...}
    On failure: {success: false, error: {code: "...", message: "..."}}
    """
    success: bool
    metadata: Optional[ResponseMetadata] = None
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
