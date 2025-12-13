"""
Rotas de segmentos de mídia.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.media_segment_service import MediaSegmentService
from app.services.channel_service import ChannelService
from app.schemas.media_segment import MediaSegmentSchema, MediaSegmentCreateSchema

router = APIRouter(prefix="/ai/segments", tags=["media_segments"])


@router.post("", response_model=MediaSegmentSchema)
async def upload_segment(
    segment_data: MediaSegmentCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload de segmento para análise."""
    channel = ChannelService.get_channel_by_id(db, segment_data.channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    segment = MediaSegmentService.create_segment(
        db,
        channel_id=segment_data.channel_id,
        segment_type=segment_data.segment_type,
        start_time=segment_data.start_time,
        end_time=segment_data.end_time,
        duration_seconds=segment_data.duration_seconds,
        file_path=segment_data.file_path,
        recording_id=segment_data.recording_id,
        file_size_bytes=segment_data.file_size_bytes
    )
    
    return segment


@router.get("/{segment_id}", response_model=MediaSegmentSchema)
async def get_segment(
    segment_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Status do segmento."""
    segment = MediaSegmentService.get_segment_by_id(db, segment_id)
    
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento não encontrado"
        )
    
    return segment
