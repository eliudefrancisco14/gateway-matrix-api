"""
Schemas Pydantic para gravações.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class RecordingSchema(BaseModel):
    """Schema de gravação (resposta)."""
    id: UUID
    channel_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    format: Optional[str] = None
    status: str
    meta_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class RecordingCreateSchema(BaseModel):
    """Schema para criar gravação."""
    channel_id: UUID
