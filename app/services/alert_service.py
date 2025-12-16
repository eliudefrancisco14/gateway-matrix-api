"""
Serviço de alertas.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.alert import Alert
from uuid import UUID
from typing import Optional, List
from datetime import datetime


class AlertService:
    """Serviço para gerenciar alertas."""
    
    @staticmethod
    def create_alert(
        db: Session,
        severity: str,
        message: str,
        source_id: Optional[UUID] = None,
        channel_id: Optional[UUID] = None
    ) -> Alert:
        """Cria um novo alerta."""
        alert = Alert(
            severity=severity,
            message=message,
            source_id=source_id,
            channel_id=channel_id
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    def get_all_alerts(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        source_id: Optional[UUID] = None,
        channel_id: Optional[UUID] = None
    ) -> List[Alert]:
        """Obtém todos os alertas com filtros."""
        query = db.query(Alert)
        
        if severity:
            query = query.filter(Alert.severity == severity)
        if acknowledged is not None:
            query = query.filter(Alert.acknowledged == acknowledged)
        if source_id:
            query = query.filter(Alert.source_id == source_id)
        if channel_id:
            query = query.filter(Alert.channel_id == channel_id)
        
        return query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_alert_counts(db: Session) -> dict:
        """Retorna contagens de alertas por severidade."""
        result = db.query(
            Alert.severity,
            func.count(Alert.id).label('count')
        ).group_by(Alert.severity).all()
        
        counts = {"critical": 0, "error": 0, "warning": 0, "info": 0}
        
        for severity, count in result:
            counts[severity] = count
        
        unacknowledged = db.query(Alert).filter(Alert.acknowledged == False).count()
        
        return {
            **counts,
            "total": sum(counts.values()),
            "unacknowledged": unacknowledged
        }
    
    @staticmethod
    def acknowledge_alert(db: Session, alert_id: UUID, user_id: UUID) -> Optional[Alert]:
        """Marca um alerta como reconhecido."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = user_id
            alert.acknowledged_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)
        return alert