"""
Rotas de alertas.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.alert_service import AlertService
from app.schemas.alert import AlertSchema, AlertCountsSchema
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=PaginatedResponse[AlertSchema])
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    severity: str = Query(None),
    acknowledged: bool = Query(None),
    source_id: UUID = Query(None),
    channel_id: UUID = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista alertas com filtros."""
    from app.models.alert import Alert
    
    # Contar total
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity)
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)
    if source_id:
        query = query.filter(Alert.source_id == source_id)
    if channel_id:
        query = query.filter(Alert.channel_id == channel_id)
    
    total = query.count()
    
    # Buscar alertas
    alerts = AlertService.get_all_alerts(
        db, skip=skip, limit=limit,
        severity=severity, acknowledged=acknowledged,
        source_id=source_id, channel_id=channel_id
    )
    
    return PaginatedResponse[AlertSchema].create(
        items=alerts,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/counts", response_model=AlertCountsSchema)
async def get_alert_counts(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna contagens de alertas."""
    counts = AlertService.get_alert_counts(db)
    return counts


@router.post("/{alert_id}/acknowledge", response_model=AlertSchema)
async def acknowledge_alert(
    alert_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marca alerta como reconhecido."""
    alert = AlertService.acknowledge_alert(db, alert_id, UUID(current_user["user_id"]))
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta não encontrado"
        )
    
    return alert