"""
Modelos para análises de IA: AIAnalysis, Transcription, ContentAnalysis, Summary, AIInsight.
"""
from sqlalchemy import Column, String, DateTime, Enum, Text, Integer, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class AnalysisType(str, enum.Enum):
    """Enum de tipos de análise."""
    TRANSCRIPTION = "transcription"
    SUMMARY = "summary"
    ENTITIES = "entities"
    EMOTIONS = "emotions"
    THEMES = "themes"
    FULL = "full"


class AnalysisStatus(str, enum.Enum):
    """Enum de status de análise."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InsightType(str, enum.Enum):
    """Enum de tipos de insight."""
    ALERT = "alert"
    RECOMMENDATION = "recommendation"
    ANOMALY = "anomaly"
    TREND = "trend"
    SUMMARY = "summary"


class Severity(str, enum.Enum):
    """Enum de severidade."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SummaryType(str, enum.Enum):
    """Enum de tipos de resumo."""
    BRIEF = "brief"
    DETAILED = "detailed"
    BULLETS = "bullets"
    EXECUTIVE = "executive"


class AIAnalysis(Base):
    """Modelo de análise de IA."""
    __tablename__ = "ai_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(UUID(as_uuid=True), ForeignKey("media_segments.id"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    analysis_type = Column(Enum(AnalysisType), nullable=False)
    status = Column(Enum(AnalysisStatus), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    model_used = Column(String(100))
    model_version = Column(String(50))
    processing_time_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relacionamentos
    segment = relationship("MediaSegment", back_populates="analyses")
    transcription = relationship("Transcription", uselist=False, back_populates="analysis", cascade="all, delete-orphan")
    content_analysis = relationship("ContentAnalysis", uselist=False, back_populates="analysis", cascade="all, delete-orphan")
    summary = relationship("Summary", uselist=False, back_populates="analysis", cascade="all, delete-orphan")


class Transcription(Base):
    """Modelo de transcrição."""
    __tablename__ = "transcriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("ai_analyses.id"), unique=True, nullable=False)
    full_text = Column(Text)
    language = Column(String(10))
    confidence = Column(String(50))  # DECIMAL(3,2) representado como String para compatibilidade
    word_count = Column(Integer)
    segments = Column(JSONB)
    
    # Relacionamentos
    analysis = relationship("AIAnalysis", back_populates="transcription")


class ContentAnalysis(Base):
    """Modelo de análise de conteúdo."""
    __tablename__ = "content_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("ai_analyses.id"), unique=True, nullable=False)
    themes = Column(JSONB)
    entities = Column(JSONB)
    emotions = Column(JSONB)
    dominant_emotion = Column(String(50))
    sentiment_score = Column(String(50))  # DECIMAL(3,2) representado como String
    keywords = Column(JSONB)
    categories = Column(JSONB)
    
    # Relacionamentos
    analysis = relationship("AIAnalysis", back_populates="content_analysis")


class Summary(Base):
    """Modelo de resumo."""
    __tablename__ = "summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("ai_analyses.id"), unique=True, nullable=False)
    summary_type = Column(Enum(SummaryType), nullable=False)
    content = Column(Text)
    bullet_points = Column(JSONB)
    key_moments = Column(JSONB)
    word_count = Column(Integer)
    
    # Relacionamentos
    analysis = relationship("AIAnalysis", back_populates="summary")


class AIInsight(Base):
    """Modelo de insight de IA."""
    __tablename__ = "ai_insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("ai_analyses.id"))
    insight_type = Column(Enum(InsightType), nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    data = Column(JSONB)
    is_read = Column(String(50), default="false")  # Boolean representado como String
    is_actionable = Column(String(50), nullable=False)  # Boolean representado como String
    action_taken = Column(String(50), default="false")  # Boolean representado como String
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
