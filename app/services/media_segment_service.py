"""
Serviço de segmentos de mídia.
"""
from sqlalchemy.orm import Session
from app.models.media_segment import MediaSegment
from uuid import UUID
from typing import Optional, List
from datetime import datetime


class MediaSegmentService:
    """Serviço para gerenciar segmentos de mídia."""
    
    @staticmethod
    def create_segment(db: Session, channel_id: UUID, segment_type: str,
                      start_time: datetime, end_time: datetime, duration_seconds: int,
                      file_path: str, **kwargs) -> MediaSegment:
        """Cria um novo segmento de mídia."""
        segment = MediaSegment(
            channel_id=channel_id,
            segment_type=segment_type,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            file_path=file_path,
            status="pending",
            **kwargs
        )
        db.add(segment)
        db.commit()
        db.refresh(segment)
        return segment
    
    @staticmethod
    def get_segment_by_id(db: Session, segment_id: UUID) -> Optional[MediaSegment]:
        """Obtém um segmento pelo ID."""
        return db.query(MediaSegment).filter(MediaSegment.id == segment_id).first()
    
    @staticmethod
    def get_all_segments(db: Session, skip: int = 0, limit: int = 10,
                        channel_id: Optional[UUID] = None, status: Optional[str] = None) -> List[MediaSegment]:
        """Obtém todos os segmentos com paginação e filtros."""
        query = db.query(MediaSegment)
        
        if channel_id:
            query = query.filter(MediaSegment.channel_id == channel_id)
        if status:
            query = query.filter(MediaSegment.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_segment(db: Session, segment_id: UUID, **kwargs) -> Optional[MediaSegment]:
        """Atualiza um segmento."""
        segment = MediaSegmentService.get_segment_by_id(db, segment_id)
        if segment:
            for key, value in kwargs.items():
                if value is not None and hasattr(segment, key):
                    setattr(segment, key, value)
            db.commit()
            db.refresh(segment)
        return segment
    
    @staticmethod
    def delete_segment(db: Session, segment_id: UUID) -> bool:
        """Remove um segmento."""
        segment = MediaSegmentService.get_segment_by_id(db, segment_id)
        if segment:
            db.delete(segment)
            db.commit()
            return True
        return False
