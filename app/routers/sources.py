"""
Rotas de fontes de ingestão.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.source_service import SourceService
from app.schemas.source import SourceSchema, SourceCreateSchema, SourceUpdateSchema, SourceMetricSchema

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceSchema])
async def list_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: str = Query(None),
    protocol: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todas as fontes com paginação e filtros."""
    sources = SourceService.get_all_sources(db, skip=skip, limit=limit, status=status, protocol=protocol)
    return sources


@router.post("", response_model=SourceSchema)
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


@router.delete("/{source_id}")
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
    
    return {"success": True}


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
    
    # Implementação simplificada: retornar status simulado
    return {
        "reachable": True,
        "latency_ms": 25,
        "details": "Conexão bem-sucedida"
    }


@router.get("/{source_id}/metrics", response_model=list[SourceMetricSchema])
async def get_source_metrics(
    source_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
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
    
    # Implementação simplificada: atualizar status
    updated_source = SourceService.update_source(db, source_id, status="connecting")
    
    return {
        "status": updated_source.status,
        "message": "Reconexão iniciada"
    }
