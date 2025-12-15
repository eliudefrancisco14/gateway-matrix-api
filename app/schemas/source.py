"""
Schemas Pydantic para fontes de ingestão (atualizado com validação YouTube e multicast).
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import re


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
    name: str = Field(..., min_length=1, max_length=255, description="Nome da fonte")
    protocol: str = Field(
        ...,
        description="Protocolo (srt, udp, rtsp, http_ts, hls, dash, youtube, file)"
    )
    source_type: str = Field(
        ...,
        description="Tipo (direct_link, satellite_encoder, local_device, cloud_origin)"
    )
    endpoint_url: str = Field(..., description="URL do endpoint")
    backup_url: Optional[str] = Field(None, description="URL de backup")
    connection_params: Optional[Dict[str, Any]] = Field(
        None,
        description="Parâmetros de conexão específicos do protocolo"
    )
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")
    
    @validator('protocol')
    def validate_protocol(cls, v):
        """Valida protocolo."""
        valid_protocols = ['srt', 'udp', 'rtsp', 'http_ts', 'hls', 'dash', 'youtube', 'file']
        if v not in valid_protocols:
            raise ValueError(f"protocol deve ser um de: {', '.join(valid_protocols)}")
        return v
    
    @validator('source_type')
    def validate_source_type(cls, v):
        """Valida tipo de fonte."""
        valid_types = ['direct_link', 'satellite_encoder', 'local_device', 'cloud_origin']
        if v not in valid_types:
            raise ValueError(f"source_type deve ser um de: {', '.join(valid_types)}")
        return v
    
    @validator('endpoint_url')
    def validate_endpoint_url(cls, v, values):
        """Valida URL do endpoint baseado no protocolo."""
        if 'protocol' not in values:
            return v
        
        protocol = values['protocol']
        
        # Validação específica para YouTube
        if protocol == 'youtube':
            # Padrões de URL do YouTube
            youtube_patterns = [
                r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
                r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([a-zA-Z0-9_-]{11})',
                r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})',
            ]
            
            is_valid_youtube = any(re.match(pattern, v) for pattern in youtube_patterns)
            
            if not is_valid_youtube:
                raise ValueError(
                    "URL do YouTube inválida. Use formato: "
                    "https://www.youtube.com/watch?v=VIDEO_ID ou "
                    "https://youtu.be/VIDEO_ID"
                )
        
        # Validação básica de URL para outros protocolos
        elif protocol in ['srt', 'udp', 'rtsp', 'http_ts', 'hls', 'dash']:
            if not v.startswith(('srt://', 'udp://', 'rtsp://', 'http://', 'https://')):
                raise ValueError(f"URL deve começar com o protocolo apropriado para {protocol}")
        
        return v
    
    @validator('connection_params')
    def validate_connection_params(cls, v, values):
        """Valida parâmetros de conexão específicos do protocolo."""
        if v is None:
            return v
        
        if 'protocol' not in values:
            return v
        
        protocol = values['protocol']
        
        # Validação para UDP com multicast
        if protocol == 'udp' and 'multicast_group' in v:
            multicast_group = v['multicast_group']
            # Validar formato de IP multicast (224.0.0.0 a 239.255.255.255)
            if not re.match(r'^(22[4-9]|23[0-9])\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$', multicast_group):
                raise ValueError(
                    "multicast_group deve ser um endereço IP multicast válido (224.0.0.0 - 239.255.255.255)"
                )
        
        return v
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "name": "Fonte SRT Principal",
                    "protocol": "srt",
                    "source_type": "satellite_encoder",
                    "endpoint_url": "srt://192.168.1.100:9000",
                    "connection_params": {
                        "latency": 200,
                        "mode": "caller"
                    }
                },
                {
                    "name": "Stream YouTube Live",
                    "protocol": "youtube",
                    "source_type": "cloud_origin",
                    "endpoint_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "meta_data": {
                        "channel_name": "Canal Exemplo"
                    }
                },
                {
                    "name": "UDP Multicast",
                    "protocol": "udp",
                    "source_type": "local_device",
                    "endpoint_url": "udp://239.1.1.1:1234",
                    "connection_params": {
                        "multicast_group": "239.1.1.1",
                        "buffer_size": 212992
                    }
                }
            ]
        }


class SourceUpdateSchema(BaseModel):
    """Schema para atualizar fonte."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    endpoint_url: Optional[str] = None
    backup_url: Optional[str] = None
    connection_params: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    meta_data: Optional[Dict[str, Any]] = None
    
    @validator('status')
    def validate_status(cls, v):
        """Valida status."""
        if v is not None:
            valid_statuses = ['online', 'offline', 'unstable', 'connecting', 'error']
            if v not in valid_statuses:
                raise ValueError(f"status deve ser um de: {', '.join(valid_statuses)}")
        return v
    
    @validator('endpoint_url')
    def validate_endpoint_url(cls, v):
        """Validação básica de URL."""
        if v is not None:
            if not v.startswith(('srt://', 'udp://', 'rtsp://', 'http://', 'https://', 'file://')):
                raise ValueError("URL deve começar com um protocolo válido")
        return v