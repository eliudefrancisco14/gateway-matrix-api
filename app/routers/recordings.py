"""
Rotas de gravações (modificado com endpoints de download/playback).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
from pathlib import Path
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.recording_service import RecordingService
from app.services.channel_service import ChannelService
from app.schemas.recording import RecordingSchema, RecordingCreateSchema

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("", response_model=dict)
async def list_recordings(
    skip: int = Query(0, ge=0, description="Número de registros a pular"),
    limit: int = Query(10, ge=1, le=100, description="Limite de registros por página"),
    channel_id: UUID = Query(None, description="Filtrar por canal"),
    status: str = Query(None, description="Filtrar por status"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todas as gravações com paginação e filtros."""
    recordings = RecordingService.get_all_recordings(
        db, skip=skip, limit=limit, channel_id=channel_id, status=status
    )
    
    from app.models.recording import Recording
    total_query = db.query(Recording)
    if channel_id:
        total_query = total_query.filter(Recording.channel_id == channel_id)
    if status:
        total_query = total_query.filter(Recording.status == status)
    
    total = total_query.count()
    
    return {
        "items": recordings,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=RecordingSchema, status_code=status.HTTP_201_CREATED)
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
    
    # Verificar se já existe gravação ativa
    from app.models.recording import Recording
    active_recording = db.query(Recording).filter(
        Recording.channel_id == recording_data.channel_id,
        Recording.status == "recording"
    ).first()
    
    if active_recording:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal já está sendo gravado"
        )
    
    # Usar o recording worker para iniciar gravação
    from app.workers.recording_worker import recording_worker
    
    try:
        recording = await recording_worker.start_manual_recording(db, recording_data.channel_id)
        return recording
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar gravação: {str(e)}"
        )


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
    
    # Usar o recording worker para parar
    from app.workers.recording_worker import recording_worker
    
    success = await recording_worker.stop_manual_recording(db, recording_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao parar gravação"
        )
    
    stopped_recording = RecordingService.get_recording_by_id(db, recording_id)
    return stopped_recording


@router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
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
            detail="Não pode remover uma gravação em andamento. Pare primeiro."
        )
    
    success = RecordingService.delete_recording(db, recording_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    return None


@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Faz download de uma gravação."""
    recording = RecordingService.get_recording_by_id(db, recording_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    if not recording.file_path or recording.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gravação não está disponível para download"
        )
    
    file_path = Path(recording.file_path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficheiro de gravação não encontrado"
        )
    
    # Obter canal para nome do ficheiro
    channel = ChannelService.get_channel_by_id(db, recording.channel_id)
    filename = f"{channel.slug}_{recording.started_at.strftime('%Y%m%d_%H%M%S')}.{recording.format}"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )


@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna URL para reprodução da gravação."""
    recording = RecordingService.get_recording_by_id(db, recording_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    if not recording.file_path or recording.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gravação não está disponível para reprodução"
        )
    
    # Retornar metadados para o player
    return {
        "recording_id": str(recording.id),
        "playback_url": f"/recordings/{recording_id}/stream",
        "format": recording.format,
        "duration_seconds": recording.duration_seconds,
        "file_size_bytes": recording.file_size_bytes,
        "started_at": recording.started_at.isoformat(),
        "ended_at": recording.ended_at.isoformat() if recording.ended_at else None
    }


@router.get("/{recording_id}/stream")
async def stream_recording(
    recording_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream da gravação (para reprodução no player)."""
    recording = RecordingService.get_recording_by_id(db, recording_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    if not recording.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ficheiro não disponível"
        )
    
    file_path = Path(recording.file_path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficheiro não encontrado"
        )
    
    # Determinar media type
    media_type = "video/mp4" if recording.format == "mp4" else "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type
    )


@router.post("/{recording_id}/export")
async def export_recording(
    recording_id: UUID,
    export_format: str = Query("mp4", description="Formato de exportação (mp4, mov, mkv)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exporta gravação para formato específico."""
    recording = RecordingService.get_recording_by_id(db, recording_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gravação não encontrada"
        )
    
    if recording.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gravação não está completa"
        )
    
    # Validar formato
    valid_formats = ["mp4", "mov", "mkv", "avi"]
    if export_format not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato inválido. Use: {', '.join(valid_formats)}"
        )
    
    export_path = await RecordingService.export_recording(db, recording_id, export_format)
    
    if not export_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao exportar gravação"
        )
    
    return {
        "export_path": export_path,
        "download_url": f"/recordings/{recording_id}/download?format={export_format}"
    }


@router.get("/summary/statistics")
async def get_recordings_summary(
    channel_id: UUID = Query(None, description="Filtrar por canal"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém estatísticas de gravações."""
    summary = RecordingService.get_recordings_summary(db, channel_id)
    
    return summary