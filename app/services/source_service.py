"""
Serviço de fontes de ingestão.
"""
from sqlalchemy.orm import Session
from app.models.source import Source, SourceMetric
from uuid import UUID
from typing import Optional, List
from datetime import datetime


class SourceService:
    """Serviço para gerenciar fontes de ingestão."""
    
    @staticmethod
    def create_source(db: Session, name: str, protocol: str, source_type: str,
                     endpoint_url: str, created_by: UUID, **kwargs) -> Source:
        """Cria uma nova fonte."""
        source = Source(
            name=name,
            protocol=protocol,
            source_type=source_type,
            endpoint_url=endpoint_url,
            created_by=created_by,
            status="offline",
            **kwargs
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source
    
    @staticmethod
    def get_source_by_id(db: Session, source_id: UUID) -> Optional[Source]:
        """Obtém uma fonte pelo ID."""
        return db.query(Source).filter(Source.id == source_id).first()
    
    @staticmethod
    def get_all_sources(db: Session, skip: int = 0, limit: int = 10,
                       status: Optional[str] = None, protocol: Optional[str] = None) -> List[Source]:
        """Obtém todas as fontes com paginação e filtros."""
        query = db.query(Source)
        
        if status:
            query = query.filter(Source.status == status)
        if protocol:
            query = query.filter(Source.protocol == protocol)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_source(db: Session, source_id: UUID, **kwargs) -> Optional[Source]:
        """Atualiza uma fonte."""
        source = SourceService.get_source_by_id(db, source_id)
        if source:
            for key, value in kwargs.items():
                if value is not None and hasattr(source, key):
                    setattr(source, key, value)
            source.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(source)
        return source
    
    @staticmethod
    def delete_source(db: Session, source_id: UUID) -> bool:
        """Remove uma fonte."""
        source = SourceService.get_source_by_id(db, source_id)
        if source:
            db.delete(source)
            db.commit()
            return True
        return False
    
    @staticmethod
    def add_metric(db: Session, source_id: UUID, **metric_data) -> SourceMetric:
        """Adiciona uma métrica a uma fonte."""
        metric = SourceMetric(
            source_id=source_id,
            timestamp=datetime.utcnow(),
            **metric_data
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric
    
    @staticmethod
    def get_metrics(db: Session, source_id: UUID, limit: int = 100) -> List[SourceMetric]:
        """Obtém as métricas de uma fonte."""
        return db.query(SourceMetric).filter(SourceMetric.source_id == source_id).order_by(
            SourceMetric.timestamp.desc()
        ).limit(limit).all()
