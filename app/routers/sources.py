"""
Rotas de fontes de ingestão (modificado com endpoints de teste e reconexão).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.source_service import SourceService
from app.schemas.source import SourceSchema, SourceCreateSchema, SourceUpdateSchema, SourceMetricSchema

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
async def list_sources(
    skip: int = Query(0, ge=0, description="Número de registros a pular"),
    limit: int = Query(10, ge=1, le=100, description="Limite de registros por página"),
    status: str = Query(None, description="Filtrar por status"),
    protocol: str = Query(None, description="Filtrar por protocolo"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todas as fontes com paginação e filtros."""
    from app.models.source import Source
    from app.schemas.pagination import PaginatedResponse
    from app.schemas.source import SourceSchema
    
    # Contar total com filtros
    query = db.query(Source).filter(Source.is_active == True)
    
    if status:
        query = query.filter(Source.status == status)
    if protocol:
        query = query.filter(Source.protocol == protocol)
    
    total = query.count()
    
    # Buscar itens paginados
    sources = SourceService.get_all_sources(db, skip=skip, limit=limit, status=status, protocol=protocol)
    
    # Retornar resposta paginada
    return PaginatedResponse[SourceSchema].create(
        items=sources,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("", response_model=SourceSchema, status_code=status.HTTP_201_CREATED)
async def create_source(
    source_data: SourceCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova fonte."""
    source = SourceService.create_source(
        db,
        name=source_data.name,
        protocol=source_data.protocol,
        source_type=source_data.source_type,
        endpoint_url=source_data.endpoint_url,
        created_by=UUID(current_user["user_id"]),
        backup_url=source_data.backup_url,
        connection_params=source_data.connection_params,
        meta_data=source_data.meta_data
    )
    
    return source


@router.get("/{source_id}", response_model=SourceSchema)
async def get_source(
    source_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma fonte específica."""
    source = SourceService.get_source_by_id(db, source_id)
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fonte não encontrada"
        )
    
    return source


@router.put("/{source_id}", response_model=SourceSchema)
async def update_source(
    source_id: UUID,
    source_data: SourceUpdateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza uma fonte."""
    updated_source = SourceService.update_source(db, source_id, **source_data.dict(exclude_unset=True))
    
    if not updated_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fonte não encontrada"
        )
    
    return updated_source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove uma fonte."""
    success = SourceService.delete_source(db, source_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fonte não encontrada"
        )
    
    return None


@router.post("/{source_id}/test")
async def test_source(
    source_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Testa a conectividade de uma fonte."""
    source = SourceService.get_source_by_id(db, source_id)
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fonte não encontrada"
        )
    
    # Testar conectividade usando stream probe
    result = await SourceService.test_source_connectivity(db, source_id)
    
    return result


@router.get("/{source_id}/metrics", response_model=list[SourceMetricSchema])
async def get_source_metrics(
    source_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Limite de métricas"),
    from_time: datetime = Query(None, description="Data/hora inicial (ISO 8601)"),
    to_time: datetime = Query(None, description="Data/hora final (ISO 8601)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém as métricas históricas de uma fonte."""
    source = SourceService.get_source_by_id(db, source_id)
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fonte não encontrada"
        )
    
    # Obter métricas com filtros de período
    if from_time or to_time:
        metrics = SourceService.get_metrics_history(
            db,
            source_id,
            from_time=from_time,
            to_time=to_time,
            limit=limit
        )
    else:
        metrics = SourceService.get_metrics(db, source_id, limit=limit)
    
    return metrics


@router.post("/{source_id}/reconnect")
async def reconnect_source(
    source_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Força a reconexão de uma fonte."""
    source = SourceService.get_source_by_id(db, source_id)
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fonte não encontrada"
        )
    
    # Iniciar reconexão
    success = await SourceService.reconnect_source(db, source_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao iniciar reconexão"
        )
    
    return {
        "status": "connecting",
        "message": "Reconexão iniciada"
    }


@router.get("/summary/status")
async def get_sources_status_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém resumo de status de todas as fontes."""
    summary = SourceService.get_source_status_summary(db)
    
    return {
        "summary": summary,
        "total": sum(summary.values())
    }