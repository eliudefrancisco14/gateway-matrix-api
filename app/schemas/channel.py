"""
Schemas Pydantic para canais de transmissão (atualizado com validação de recording_enabled).
"""
from pydantic import BaseModel, Field, validator
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
    recording_enabled: bool = Field(
        default=False,
        description="Se True, o canal será gravado automaticamente quando estiver live"
    )
    
    class Config:
        from_attributes = True


class ChannelCreateSchema(BaseModel):
    """Schema para criar canal."""
    name: str = Field(..., min_length=1, max_length=255, description="Nome do canal")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern="^[a-z0-9-]+$",
        description="Slug único (apenas letras minúsculas, números e hífen)"
    )
    source_id: Optional[UUID] = Field(None, description="ID da fonte principal")
    fallback_source_id: Optional[UUID] = Field(None, description="ID da fonte de backup")
    output_format: str = Field(
        default="hls",
        description="Formato de saída (hls, dash, both)"
    )
    category: Optional[str] = Field(None, max_length=100, description="Categoria do canal")
    priority: int = Field(default=0, ge=0, le=100, description="Prioridade (0-100)")
    max_viewers: Optional[int] = Field(None, ge=0, description="Número máximo de viewers")
    transcoding_profile: Optional[str] = Field(
        None,
        max_length=100,
        description="Perfil de transcodificação (ex: 720p, 1080p)"
    )
    recording_enabled: bool = Field(
        default=False,
        description="Ativar gravação automática quando o canal estiver live"
    )
    
    @validator('output_format')
    def validate_output_format(cls, v):
        """Valida formato de saída."""
        valid_formats = ['hls', 'dash', 'both']
        if v not in valid_formats:
            raise ValueError(f"output_format deve ser um de: {', '.join(valid_formats)}")
        return v
    
    @validator('slug')
    def validate_slug(cls, v):
        """Valida slug."""
        if not v.islower():
            raise ValueError("slug deve estar em minúsculas")
        if '--' in v:
            raise ValueError("slug não pode conter hífens consecutivos")
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("slug não pode começar ou terminar com hífen")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Canal Principal",
                "slug": "canal-principal",
                "output_format": "hls",
                "category": "Notícias",
                "priority": 10,
                "recording_enabled": True
            }
        }


class ChannelUpdateSchema(BaseModel):
    """Schema para atualizar canal."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    source_id: Optional[UUID] = None
    fallback_source_id: Optional[UUID] = None
    status: Optional[str] = None
    output_format: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    priority: Optional[int] = Field(None, ge=0, le=100)
    max_viewers: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    transcoding_profile: Optional[str] = Field(None, max_length=100)
    recording_enabled: Optional[bool] = Field(
        None,
        description="Ativar/desativar gravação automática"
    )
    
    @validator('output_format')
    def validate_output_format(cls, v):
        """Valida formato de saída."""
        if v is not None:
            valid_formats = ['hls', 'dash', 'both']
            if v not in valid_formats:
                raise ValueError(f"output_format deve ser um de: {', '.join(valid_formats)}")
        return v
    
    @validator('status')
    def validate_status(cls, v):
        """Valida status."""
        if v is not None:
            valid_statuses = ['live', 'offline', 'scheduled', 'error', 'maintenance']
            if v not in valid_statuses:
                raise ValueError(f"status deve ser um de: {', '.join(valid_statuses)}")
        return v
    
    @validator('slug')
    def validate_slug(cls, v):
        """Valida slug."""
        if v is not None:
            if not v.islower():
                raise ValueError("slug deve estar em minúsculas")
            if '--' in v:
                raise ValueError("slug não pode conter hífens consecutivos")
            if v.startswith('-') or v.endswith('-'):
                raise ValueError("slug não pode começar ou terminar com hífen")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Canal Principal (Atualizado)",
                "priority": 20,
                "recording_enabled": True
            }
        }