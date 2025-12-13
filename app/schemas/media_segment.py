"""
Schemas Pydantic para segmentos de mídia.
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class MediaSegmentSchema(BaseModel):
    """Schema de segmento de mídia (resposta)."""
    id: UUID
    channel_id: UUID
    recording_id: Optional[UUID] = None
    segment_type: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    file_path: str
    file_size_bytes: Optional[int] = None
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MediaSegmentCreateSchema(BaseModel):
    """Schema para criar segmento de mídia."""
    channel_id: UUID
    recording_id: Optional[UUID] = None
    segment_type: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    file_path: str
    file_size_bytes: Optional[int] = None
