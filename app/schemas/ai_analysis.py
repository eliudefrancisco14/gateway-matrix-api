"""
Schemas Pydantic para análises de IA.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


class TranscriptionSchema(BaseModel):
    """Schema de transcrição."""
    id: UUID
    analysis_id: UUID
    full_text: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    word_count: Optional[int] = None
    segments: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        from_attributes = True


class ContentAnalysisSchema(BaseModel):
    """Schema de análise de conteúdo."""
    id: UUID
    analysis_id: UUID
    themes: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    emotions: Optional[List[Dict[str, Any]]] = None
    dominant_emotion: Optional[str] = None
    sentiment_score: Optional[float] = None
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class SummarySchema(BaseModel):
    """Schema de resumo."""
    id: UUID
    analysis_id: UUID
    summary_type: str
    content: Optional[str] = None
    bullet_points: Optional[List[str]] = None
    key_moments: Optional[List[Dict[str, Any]]] = None
    word_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class AIAnalysisSchema(BaseModel):
    """Schema de análise de IA (resposta)."""
    id: UUID
    segment_id: UUID
    channel_id: UUID
    analysis_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_used: Optional[str] = None
    model_version: Optional[str] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    transcription: Optional[TranscriptionSchema] = None
    content_analysis: Optional[ContentAnalysisSchema] = None
    summary: Optional[SummarySchema] = None
    
    class Config:
        from_attributes = True


class AnalysisCreateSchema(BaseModel):
    """Schema para criar análise."""
    segment_id: UUID
    analysis_types: List[str]


class AIInsightSchema(BaseModel):
    """Schema de insight de IA."""
    id: UUID
    channel_id: UUID
    analysis_id: Optional[UUID] = None
    insight_type: str
    severity: str
    title: str
    description: str
    data: Optional[Dict[str, Any]] = None
    is_read: bool = False
    is_actionable: bool
    action_taken: bool = False
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
