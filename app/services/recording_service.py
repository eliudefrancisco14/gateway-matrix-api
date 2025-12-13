"""
Serviço de gravações.
"""
from sqlalchemy.orm import Session
from app.models.recording import Recording
from uuid import UUID
from typing import Optional, List
from datetime import datetime


class RecordingService:
    """Serviço para gerenciar gravações."""
    
    @staticmethod
    def create_recording(db: Session, channel_id: UUID, **kwargs) -> Recording:
        """Cria uma nova gravação."""
        recording = Recording(
            channel_id=channel_id,
            started_at=datetime.utcnow(),
            status="recording",
            **kwargs
        )
        db.add(recording)
        db.commit()
        db.refresh(recording)
        return recording
    
    @staticmethod
    def get_recording_by_id(db: Session, recording_id: UUID) -> Optional[Recording]:
        """Obtém uma gravação pelo ID."""
        return db.query(Recording).filter(Recording.id == recording_id).first()
    
    @staticmethod
    def get_all_recordings(db: Session, skip: int = 0, limit: int = 10,
                          channel_id: Optional[UUID] = None, status: Optional[str] = None) -> List[Recording]:
        """Obtém todas as gravações com paginação e filtros."""
        query = db.query(Recording)
        
        if channel_id:
            query = query.filter(Recording.channel_id == channel_id)
        if status:
            query = query.filter(Recording.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_recording(db: Session, recording_id: UUID, **kwargs) -> Optional[Recording]:
        """Atualiza uma gravação."""
        recording = RecordingService.get_recording_by_id(db, recording_id)
        if recording:
            for key, value in kwargs.items():
                if value is not None and hasattr(recording, key):
                    setattr(recording, key, value)
            db.commit()
            db.refresh(recording)
        return recording
    
    @staticmethod
    def stop_recording(db: Session, recording_id: UUID) -> Optional[Recording]:
        """Para uma gravação."""
        recording = RecordingService.get_recording_by_id(db, recording_id)
        if recording:
            recording.ended_at = datetime.utcnow()
            recording.status = "completed"
            if recording.started_at:
                recording.duration_seconds = int((recording.ended_at - recording.started_at).total_seconds())
            db.commit()
            db.refresh(recording)
        return recording
    
    @staticmethod
    def delete_recording(db: Session, recording_id: UUID) -> bool:
        """Remove uma gravação."""
        recording = RecordingService.get_recording_by_id(db, recording_id)
        if recording:
            db.delete(recording)
            db.commit()
            return True
        return False
