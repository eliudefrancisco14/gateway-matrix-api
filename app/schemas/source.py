"""
Schemas Pydantic para fontes de ingestão.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class SourceMetricSchema(BaseModel):
    """Schema de métrica de fonte."""
    id: int
    source_id: UUID
    timestamp: datetime
    bitrate_kbps: Optional[int] = None
    fps: Optional[float] = None
    latency_ms: Optional[int] = None
    packet_loss_percent: Optional[float] = None
    jitter_ms: Optional[int] = None
    buffer_health: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    resolution: Optional[str] = None
    error_count: int = 0
    
    class Config:
        from_attributes = True


class SourceSchema(BaseModel):
    """Schema de fonte (resposta)."""
    id: UUID
    name: str
    protocol: str
    source_type: str
    endpoint_url: str
    backup_url: Optional[str] = None
    connection_params: Optional[Dict[str, Any]] = None
    status: str
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    meta_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class SourceCreateSchema(BaseModel):
    """Schema para criar fonte."""
    name: str
    protocol: str
    source_type: str
    endpoint_url: str
    backup_url: Optional[str] = None
    connection_params: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None


class SourceUpdateSchema(BaseModel):
    """Schema para atualizar fonte."""
    name: Optional[str] = None
    endpoint_url: Optional[str] = None
    backup_url: Optional[str] = None
    connection_params: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    meta_data: Optional[Dict[str, Any]] = None
