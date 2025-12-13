"""
Modelo Recording para gerenciar gravações de canais.
"""
from sqlalchemy import Column, String, DateTime, Enum, Text, Integer, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class RecordingStatus(str, enum.Enum):
    """Enum de status de gravação."""
    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"
    PROCESSING = "processing"


class Recording(Base):
    """Modelo de gravação."""
    __tablename__ = "recordings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    file_path = Column(Text)
    file_size_bytes = Column(BigInteger)
    format = Column(String(20))
    status = Column(Enum(RecordingStatus), nullable=False)
    meta_data = Column(JSONB)
    
    # Relacionamentos
    channel = relationship("Channel", back_populates="recordings")
    media_segments = relationship("MediaSegment", back_populates="recording", cascade="all, delete-orphan")
