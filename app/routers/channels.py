"""
Rotas de canais de transmissão.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.channel_service import ChannelService
from app.services.source_service import SourceService
from app.schemas.channel import ChannelSchema, ChannelCreateSchema, ChannelUpdateSchema, ChannelEventSchema

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=list[ChannelSchema])
async def list_channels(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: str = Query(None),
    category: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todos os canais com paginação e filtros."""
    channels = ChannelService.get_all_channels(db, skip=skip, limit=limit, status=status, category=category)
    return channels


@router.post("", response_model=ChannelSchema)
async def create_channel(
    channel_data: ChannelCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria um novo canal."""
    # Validar se source_id existe (se fornecido)
    if channel_data.source_id:
        source = SourceService.get_source_by_id(db, channel_data.source_id)
        if not source:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fonte não encontrada"
            )
    
    channel = ChannelService.create_channel(
        db,
        name=channel_data.name,
        slug=channel_data.slug,
        output_format=channel_data.output_format,
        created_by=UUID(current_user["user_id"]),
        source_id=channel_data.source_id,
        fallback_source_id=channel_data.fallback_source_id,
        category=channel_data.category,
        priority=channel_data.priority,
        max_viewers=channel_data.max_viewers,
        transcoding_profile=channel_data.transcoding_profile,
        recording_enabled=channel_data.recording_enabled
    )
    
    return channel


@router.get("/{channel_id}", response_model=ChannelSchema)
async def get_channel(
    channel_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um canal específico."""
    channel = ChannelService.get_channel_by_id(db, channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    return channel


@router.put("/{channel_id}", response_model=ChannelSchema)
async def update_channel(
    channel_id: UUID,
    channel_data: ChannelUpdateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza um canal."""
    updated_channel = ChannelService.update_channel(db, channel_id, **channel_data.dict(exclude_unset=True))
    
    if not updated_channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    return updated_channel


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove um canal."""
    channel = ChannelService.get_channel_by_id(db, channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    if channel.status == "live":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não pode remover um canal que está live"
        )
    
    success = ChannelService.delete_channel(db, channel_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    return {"success": True}


@router.post("/{channel_id}/start")
async def start_channel(
    channel_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Inicia a transmissão de um canal."""
    channel = ChannelService.get_channel_by_id(db, channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    if not channel.source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal não tem uma fonte associada"
        )
    
    updated_channel = ChannelService.update_channel(db, channel_id, status="live")
    ChannelService.add_event(db, channel_id, "started", "user", user_id=UUID(current_user["user_id"]))
    
    return {
        "status": updated_channel.status,
        "stream_url": f"/stream/{channel.slug}/manifest.m3u8"
    }


@router.post("/{channel_id}/stop")
async def stop_channel(
    channel_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Para a transmissão de um canal."""
    channel = ChannelService.get_channel_by_id(db, channel_id)
    
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
    
    updated_channel = ChannelService.update_channel(db, channel_id, status="offline")
    ChannelService.add_event(db, channel_id, "stopped", "user", user_id=UUID(current_user["user_id"]))
    
    return {"status": updated_channel.status}


@router.post("/{channel_id}/switch-source")
async def switch_source(
    channel_id: UUID,
    source_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Troca a fonte de um canal."""
    channel = ChannelService.get_channel_by_id(db, channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    source = SourceService.get_source_by_id(db, source_id)
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fonte não encontrada"
        )
    
    if source.status != "online":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fonte não está online"
        )
    
    old_source_id = channel.source_id
    updated_channel = ChannelService.update_channel(db, channel_id, source_id=source_id)
    ChannelService.add_event(
        db, channel_id, "source_changed", "user",
        details={"old_source_id": str(old_source_id), "new_source_id": str(source_id)},
        user_id=UUID(current_user["user_id"])
    )
    
    return updated_channel


@router.get("/{channel_id}/thumbnail")
async def get_thumbnail(
    channel_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém o thumbnail atual de um canal."""
    channel = ChannelService.get_channel_by_id(db, channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    if not channel.thumbnail_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail não disponível"
        )
    
    return {"thumbnail_url": channel.thumbnail_url}


@router.get("/{channel_id}/events", response_model=list[ChannelEventSchema])
async def get_channel_events(
    channel_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém o histórico de eventos de um canal."""
    channel = ChannelService.get_channel_by_id(db, channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    events = ChannelService.get_events(db, channel_id, limit=limit)
    return events
