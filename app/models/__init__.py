"""
Módulo models com os modelos SQLAlchemy.
"""
from app.models.user import User
from app.models.source import Source, SourceMetric
from app.models.channel import Channel, ChannelEvent
from app.models.recording import Recording
from app.models.media_segment import MediaSegment
from app.models.ai_analysis import AIAnalysis, Transcription, ContentAnalysis, Summary, AIInsight
from app.models.system_config import SystemConfig
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "Source",
    "SourceMetric",
    "Channel",
    "ChannelEvent",
    "Recording",
    "MediaSegment",
    "AIAnalysis",
    "Transcription",
    "ContentAnalysis",
    "Summary",
    "AIInsight",
    "SystemConfig",
    "AuditLog"
]
