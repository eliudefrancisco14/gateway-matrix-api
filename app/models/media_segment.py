"""
Modelo MediaSegment para gerenciar segmentos de mídia para análise de IA.
"""
from sqlalchemy import Column, String, DateTime, Enum, Text, Integer, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class SegmentType(str, enum.Enum):
    """Enum de tipos de segmento."""
    VIDEO = "video"
    AUDIO = "audio"
    BOTH = "both"


class SegmentStatus(str, enum.Enum):
    """Enum de status de segmento."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaSegment(Base):
    """Modelo de segmento de mídia."""
    __tablename__ = "media_segments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    recording_id = Column(UUID(as_uuid=True), ForeignKey("recordings.id"))
    segment_type = Column(Enum(SegmentType), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger)
    status = Column(Enum(SegmentStatus), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Relacionamentos
    channel = relationship("Channel", back_populates="media_segments")
    recording = relationship("Recording", back_populates="media_segments")
    analyses = relationship("AIAnalysis", back_populates="segment", cascade="all, delete-orphan")
