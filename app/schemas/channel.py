"""
Schemas Pydantic para canais de transmissão.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ChannelEventSchema(BaseModel):
    """Schema de evento de canal."""
    id: int
    channel_id: UUID
    event_type: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    triggered_by: str
    user_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True


class ChannelSchema(BaseModel):
    """Schema de canal (resposta)."""
    id: UUID
    name: str
    slug: str
    source_id: Optional[UUID] = None
    fallback_source_id: Optional[UUID] = None
    status: str
    output_format: str
    thumbnail_url: Optional[str] = None
    thumbnail_updated_at: Optional[datetime] = None
    category: Optional[str] = None
    priority: int = 0
    max_viewers: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    transcoding_profile: Optional[str] = None
    recording_enabled: bool = False
    
    class Config:
        from_attributes = True


class ChannelCreateSchema(BaseModel):
    """Schema para criar canal."""
    name: str
    slug: str
    source_id: Optional[UUID] = None
    fallback_source_id: Optional[UUID] = None
    output_format: str = "hls"
    category: Optional[str] = None
    priority: int = 0
    max_viewers: Optional[int] = None
    transcoding_profile: Optional[str] = None
    recording_enabled: bool = False


class ChannelUpdateSchema(BaseModel):
    """Schema para atualizar canal."""
    name: Optional[str] = None
    slug: Optional[str] = None
    source_id: Optional[UUID] = None
    fallback_source_id: Optional[UUID] = None
    status: Optional[str] = None
    output_format: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    max_viewers: Optional[int] = None
    is_active: Optional[bool] = None
    transcoding_profile: Optional[str] = None
    recording_enabled: Optional[bool] = None
