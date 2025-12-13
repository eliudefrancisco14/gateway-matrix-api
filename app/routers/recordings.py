"""
Rotas de gravações.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.recording_service import RecordingService
from app.services.channel_service import ChannelService
from app.schemas.recording import RecordingSchema, RecordingCreateSchema

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("", response_model=list[RecordingSchema])
async def list_recordings(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    channel_id: UUID = Query(None),
    status: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todas as gravações com paginação e filtros."""
    recordings = RecordingService.get_all_recordings(
        db, skip=skip, limit=limit, channel_id=channel_id, status=status
    )
    return recordings


@router.post("", response_model=RecordingSchema)
async def create_recording(
    recording_data: RecordingCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Inicia uma gravação manual."""
    channel = ChannelService.get_channel_by_id(db, recording_data.channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    if channel.status != "live":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal não está live"
        )
    
    recording = RecordingService.create_recording(db, recording_data.channel_id)
    
    return recording


@router.get("/{recording_id}", response_model=RecordingSchema)
async def get_recording(
    recording_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma gravação específica."""
    recording = RecordingService.get_recording_by_id(db, recording_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    return recording


@router.post("/{recording_id}/stop", response_model=RecordingSchema)
async def stop_recording(
    recording_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Para uma gravação."""
    recording = RecordingService.get_recording_by_id(db, recording_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    if recording.status != "recording":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gravação não está em andamento"
        )
    
    stopped_recording = RecordingService.stop_recording(db, recording_id)
    
    return stopped_recording


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove uma gravação."""
    recording = RecordingService.get_recording_by_id(db, recording_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    if recording.status == "recording":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não pode remover uma gravação em andamento"
        )
    
    success = RecordingService.delete_recording(db, recording_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    return {"success": True}
