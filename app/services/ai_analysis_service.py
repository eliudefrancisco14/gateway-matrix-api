"""
Serviço de análises de IA.
"""
from sqlalchemy.orm import Session
from app.models.ai_analysis import AIAnalysis, Transcription, ContentAnalysis, Summary, AIInsight
from uuid import UUID
from typing import Optional, List
from datetime import datetime


class AIAnalysisService:
    """Serviço para gerenciar análises de IA."""
    
    @staticmethod
    def create_analysis(db: Session, segment_id: UUID, channel_id: UUID,
                       analysis_type: str, created_by: Optional[UUID] = None) -> AIAnalysis:
        """Cria uma nova análise de IA."""
        analysis = AIAnalysis(
            segment_id=segment_id,
            channel_id=channel_id,
            analysis_type=analysis_type,
            status="queued",
            created_by=created_by
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    
    @staticmethod
    def get_analysis_by_id(db: Session, analysis_id: UUID) -> Optional[AIAnalysis]:
        """Obtém uma análise pelo ID."""
        return db.query(AIAnalysis).filter(AIAnalysis.id == analysis_id).first()
    
    @staticmethod
    def get_all_analyses(db: Session, skip: int = 0, limit: int = 10,
                        channel_id: Optional[UUID] = None, status: Optional[str] = None) -> List[AIAnalysis]:
        """Obtém todas as análises com paginação e filtros."""
        query = db.query(AIAnalysis)
        
        if channel_id:
            query = query.filter(AIAnalysis.channel_id == channel_id)
        if status:
            query = query.filter(AIAnalysis.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_analysis(db: Session, analysis_id: UUID, **kwargs) -> Optional[AIAnalysis]:
        """Atualiza uma análise."""
        analysis = AIAnalysisService.get_analysis_by_id(db, analysis_id)
        if analysis:
            for key, value in kwargs.items():
                if value is not None and hasattr(analysis, key):
                    setattr(analysis, key, value)
            db.commit()
            db.refresh(analysis)
        return analysis
    
    @staticmethod
    def create_insight(db: Session, channel_id: UUID, insight_type: str,
                      severity: str, title: str, description: str,
                      is_actionable: bool, **kwargs) -> AIInsight:
        """Cria um novo insight de IA."""
        insight = AIInsight(
            channel_id=channel_id,
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            is_actionable=str(is_actionable).lower(),
            **kwargs
        )
        db.add(insight)
        db.commit()
        db.refresh(insight)
        return insight
    
    @staticmethod
    def get_insight_by_id(db: Session, insight_id: UUID) -> Optional[AIInsight]:
        """Obtém um insight pelo ID."""
        return db.query(AIInsight).filter(AIInsight.id == insight_id).first()
    
    @staticmethod
    def get_all_insights(db: Session, skip: int = 0, limit: int = 10,
                        channel_id: Optional[UUID] = None, severity: Optional[str] = None) -> List[AIInsight]:
        """Obtém todos os insights com paginação e filtros."""
        query = db.query(AIInsight)
        
        if channel_id:
            query = query.filter(AIInsight.channel_id == channel_id)
        if severity:
            query = query.filter(AIInsight.severity == severity)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def mark_insight_as_read(db: Session, insight_id: UUID) -> Optional[AIInsight]:
        """Marca um insight como lido."""
        insight = AIAnalysisService.get_insight_by_id(db, insight_id)
        if insight:
            insight.is_read = "true"
            db.commit()
            db.refresh(insight)
        return insight
