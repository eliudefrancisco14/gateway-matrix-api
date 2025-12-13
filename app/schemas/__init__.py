"""
Módulo schemas com os schemas Pydantic para validação de dados.
"""
from app.schemas.user import UserSchema, UserCreateSchema, UserUpdateSchema
from app.schemas.source import SourceSchema, SourceCreateSchema, SourceUpdateSchema, SourceMetricSchema
from app.schemas.channel import ChannelSchema, ChannelCreateSchema, ChannelUpdateSchema, ChannelEventSchema
from app.schemas.recording import RecordingSchema, RecordingCreateSchema
from app.schemas.media_segment import MediaSegmentSchema, MediaSegmentCreateSchema
from app.schemas.ai_analysis import (
    AIAnalysisSchema, AnalysisCreateSchema, TranscriptionSchema,
    ContentAnalysisSchema, SummarySchema, AIInsightSchema
)
from app.schemas.auth import LoginSchema, TokenSchema, RefreshTokenSchema

__all__ = [
    "UserSchema",
    "UserCreateSchema",
    "UserUpdateSchema",
    "SourceSchema",
    "SourceCreateSchema",
    "SourceUpdateSchema",
    "SourceMetricSchema",
    "ChannelSchema",
    "ChannelCreateSchema",
    "ChannelUpdateSchema",
    "ChannelEventSchema",
    "RecordingSchema",
    "RecordingCreateSchema",
    "MediaSegmentSchema",
    "MediaSegmentCreateSchema",
    "AIAnalysisSchema",
    "AnalysisCreateSchema",
    "TranscriptionSchema",
    "ContentAnalysisSchema",
    "SummarySchema",
    "AIInsightSchema",
    "LoginSchema",
    "TokenSchema",
    "RefreshTokenSchema"
]
