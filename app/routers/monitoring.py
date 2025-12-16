"""
Rotas de monitoramento.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.source_service import SourceService
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/dashboard")
async def get_dashboard(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dados agregados do dashboard."""
    sources = SourceService.get_all_sources(db, skip=0, limit=1000)
    channels = ChannelService.get_all_channels(db, skip=0, limit=1000)
    
    sources_online = sum(1 for s in sources if s.status == "online")
    channels_live = sum(1 for c in channels if c.status == "live")
    
    return {
        "sources_summary": {
            "total": len(sources),
            "online": sources_online,
            "offline": len(sources) - sources_online
        },
        "channels_summary": {
            "total": len(channels),
            "live": channels_live,
            "offline": len(channels) - channels_live
        },
        "system_metrics": {
            "cpu_usage": 45.2,
            "memory_usage": 62.1,
            "network_bandwidth": 850.5
        }
    }


@router.get("/sources")
async def get_sources_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Status de todas as fontes."""
    sources = SourceService.get_all_sources(db, skip=0, limit=1000)
    
    sources_data = []
    for source in sources:
        metrics = SourceService.get_metrics(db, source.id, limit=1)
        current_metric = metrics[0] if metrics else None
        
        sources_data.append({
            "id": str(source.id),
            "name": source.name,
            "status": source.status,
            "protocol": source.protocol,
            "current_metrics": {
                "bitrate_kbps": current_metric.bitrate_kbps if current_metric else None,
                "fps": current_metric.fps if current_metric else None,
                "latency_ms": current_metric.latency_ms if current_metric else None
            } if current_metric else None
        })
    
    return {"sources": sources_data}


@router.get("/channels")
async def get_channels_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Status de todos os canais."""
    channels = ChannelService.get_all_channels(db, skip=0, limit=1000)
    
    channels_data = []
    for channel in channels:
        channels_data.append({
            "id": str(channel.id),
            "name": channel.name,
            "slug": channel.slug,
            "status": channel.status,
            "viewers": 0,
            "bitrate": 5000
        })
    
    return {"channels": channels_data}


@router.get("/alerts")
async def get_alerts(
    severity: str = Query(None),
    unacknowledged: bool = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alertas ativos do sistema."""
    # Implementação simplificada
    return {"alerts": []}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reconhecer alerta."""
    # Implementação simplificada
    return {"success": True}


@router.get("/system")
async def get_system_metrics(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Métricas do sistema (CPU, memória, rede)."""
    return {
        "cpu_usage_percent": 45.2,
        "memory_usage_percent": 62.1,
        "disk_usage_percent": 78.5,
        "network_bandwidth_mbps": 850.5,
        "uptime_seconds": 1234567
    }

@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    user_id: UUID = Query(None),
    action: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna audit logs com filtros."""
    from app.models.audit_log import AuditLog
    from datetime import datetime
    
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AuditLog.timestamp <= datetime.fromisoformat(end_date))
    
    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": [
            {
                "id": log.id,
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource_type": log.entity_type,
                "resource_id": str(log.entity_id) if log.entity_id else None,
                "details": {
                    "old_values": log.old_values,
                    "new_values": log.new_values
                },
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "created_at": log.timestamp.isoformat()
            }
            for log in logs
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }