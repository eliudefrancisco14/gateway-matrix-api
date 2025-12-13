"""
Modelos Channel e ChannelEvent para gerenciar canais de transmissão.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text, Integer, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class ChannelStatus(str, enum.Enum):
    """Enum de status de canal."""
    LIVE = "live"
    OFFLINE = "offline"
    SCHEDULED = "scheduled"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class OutputFormat(str, enum.Enum):
    """Enum de formatos de saída."""
    HLS = "hls"
    DASH = "dash"
    BOTH = "both"


class EventType(str, enum.Enum):
    """Enum de tipos de evento."""
    STARTED = "started"
    STOPPED = "stopped"
    FAILOVER = "failover"
    ERROR = "error"
    RECOVERED = "recovered"
    RECONNECTING = "reconnecting"
    SOURCE_CHANGED = "source_changed"


class TriggeredBy(str, enum.Enum):
    """Enum de origem do evento."""
    SYSTEM = "system"
    USER = "user"
    SCHEDULER = "scheduler"
    FAILOVER_RULE = "failover_rule"


class Channel(Base):
    """Modelo de canal de transmissão."""
    __tablename__ = "channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"))
    fallback_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"))
    status = Column(Enum(ChannelStatus), nullable=False)
    output_format = Column(Enum(OutputFormat), nullable=False)
    thumbnail_url = Column(Text)
    thumbnail_updated_at = Column(DateTime)
    category = Column(String(100))
    priority = Column(Integer, default=0)
    max_viewers = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    transcoding_profile = Column(String(100))
    recording_enabled = Column(Boolean, default=False)
    
    # Relacionamentos
    events = relationship("ChannelEvent", back_populates="channel", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="channel", cascade="all, delete-orphan")
    media_segments = relationship("MediaSegment", back_populates="channel", cascade="all, delete-orphan")


class ChannelEvent(Base):
    """Modelo de evento de canal."""
    __tablename__ = "channel_events"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    details = Column(JSONB)
    triggered_by = Column(Enum(TriggeredBy), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relacionamentos
    channel = relationship("Channel", back_populates="events")
