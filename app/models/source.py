"""
Modelos Source e SourceMetric para gerenciar fontes de ingestão.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text, Integer, DECIMAL, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class SourceProtocol(str, enum.Enum):
    """Enum de protocolos de ingestão."""
    SRT = "srt"
    UDP = "udp"
    RTSP = "rtsp"
    HTTP_TS = "http_ts"
    HLS = "hls"
    DASH = "dash"
    YOUTUBE = "youtube"
    FILE = "file"


class SourceType(str, enum.Enum):
    """Enum de tipos de fonte."""
    DIRECT_LINK = "direct_link"
    SATELLITE_ENCODER = "satellite_encoder"
    LOCAL_DEVICE = "local_device"
    CLOUD_ORIGIN = "cloud_origin"


class SourceStatus(str, enum.Enum):
    """Enum de status de fonte."""
    ONLINE = "online"
    OFFLINE = "offline"
    UNSTABLE = "unstable"
    CONNECTING = "connecting"
    ERROR = "error"


class Source(Base):
    """Modelo de fonte de ingestão."""
    __tablename__ = "sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    protocol = Column(Enum(SourceProtocol), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    endpoint_url = Column(Text, nullable=False)
    backup_url = Column(Text)
    connection_params = Column(JSONB)
    status = Column(Enum(SourceStatus), nullable=False)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSONB)
    
    # Relacionamentos
    metrics = relationship("SourceMetric", back_populates="source", cascade="all, delete-orphan")


class SourceMetric(Base):
    """Modelo de métricas de fonte."""
    __tablename__ = "source_metrics"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    bitrate_kbps = Column(Integer)
    fps = Column(DECIMAL(5, 2))
    latency_ms = Column(Integer)
    packet_loss_percent = Column(DECIMAL(5, 2))
    jitter_ms = Column(Integer)
    buffer_health = Column(DECIMAL(3, 2))
    video_codec = Column(String(50))
    audio_codec = Column(String(50))
    resolution = Column(String(20))
    error_count = Column(Integer, default=0)
    
    # Relacionamentos
    source = relationship("Source", back_populates="metrics")
    
    # Índice composto para consultas de séries temporais
    __table_args__ = (
        Index('idx_source_metrics_source_time', 'source_id', timestamp.desc()),
    )
