"""
Rotas de canais de transmissão (modificado com integração ao pipeline).
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


@router.get("", response_model=dict)
async def list_channels(
    skip: int = Query(0, ge=0, description="Número de registros a pular"),
    limit: int = Query(10, ge=1, le=100, description="Limite de registros por página"),
    status: str = Query(None, description="Filtrar por status"),
    category: str = Query(None, description="Filtrar por categoria"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todos os canais com paginação e filtros."""
    channels = ChannelService.get_all_channels(db, skip=skip, limit=limit, status=status, category=category)
    
    from app.models.channel import Channel
    total_query = db.query(Channel).filter(Channel.is_active == True)
    if status:
        total_query = total_query.filter(Channel.status == status)
    if category:
        total_query = total_query.filter(Channel.category == category)
    
    total = total_query.count()
    
    return {
        "items": channels,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=ChannelSchema, status_code=status.HTTP_201_CREATED)
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
    
    # Validar slug único
    existing = ChannelService.get_channel_by_slug(db, channel_data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug já está em uso"
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
    # Se slug está sendo alterado, validar unicidade
    if channel_data.slug:
        existing = ChannelService.get_channel_by_slug(db, channel_data.slug)
        if existing and existing.id != channel_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug já está em uso"
            )
    
    updated_channel = ChannelService.update_channel(db, channel_id, **channel_data.dict(exclude_unset=True))
    
    if not updated_channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    return updated_channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
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
            detail="Não pode remover um canal que está live. Pare o canal primeiro."
        )
    
    success = ChannelService.delete_channel(db, channel_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    return None


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
    
    if channel.status == "live":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal já está live"
        )
    
    if not channel.source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal não tem uma fonte associada"
        )
    
    try:
        result = await ChannelService.start_channel(db, channel_id, UUID(current_user["user_id"]))
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar canal: {str(e)}"
        )


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
    
    success = await ChannelService.stop_channel(db, channel_id, UUID(current_user["user_id"]))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao parar canal"
        )
    
    return {"status": "offline"}


@router.post("/{channel_id}/switch-source")
async def switch_source(
    channel_id: UUID,
    source_id: UUID = Query(..., description="ID da nova fonte"),
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
            detail=f"Fonte não está online (status: {source.status})"
        )
    
    success = await ChannelService.switch_source(db, channel_id, source_id, UUID(current_user["user_id"]))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao trocar fonte"
        )
    
    updated_channel = ChannelService.get_channel_by_id(db, channel_id)
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


@router.post("/{channel_id}/thumbnail/update")
async def update_thumbnail(
    channel_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Força atualização do thumbnail de um canal."""
    thumbnail_url = await ChannelService.update_thumbnail(db, channel_id)
    
    if not thumbnail_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível atualizar o thumbnail. Canal deve estar live."
        )
    
    return {"thumbnail_url": thumbnail_url}


@router.get("/{channel_id}/events", response_model=list[ChannelEventSchema])
async def get_channel_events(
    channel_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Limite de eventos"),
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


@router.get("/summary/status")
async def get_channels_status_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém resumo de status de todos os canais."""
    summary = ChannelService.get_channel_status_summary(db)
    
    return {
        "summary": summary,
        "total": sum(summary.values())
    }