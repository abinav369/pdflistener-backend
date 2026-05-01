from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.file_item import ProcessingStatus


class FileItemResponse(BaseModel):
    """
    Response shape that matches the Dart FileItem model exactly,
    plus backend-specific fields the app may use.
    """
    id: int
    title: str
    size: str           # e.g. "2.4 MB"
    duration: Optional[str] = None    # e.g. "18 min"
    date: str           # e.g. "Jan 15, 2025"

    # Extra backend fields
    status: ProcessingStatus
    audio_url: Optional[str] = None   # presigned/direct URL to stream audio
    created_at: datetime

    model_config = {"from_attributes": True}


class FileItemListResponse(BaseModel):
    items: list[FileItemResponse]
    total: int
