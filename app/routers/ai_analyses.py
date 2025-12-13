"""
Rotas de análises de IA.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.ai_analysis_service import AIAnalysisService
from app.services.media_segment_service import MediaSegmentService
from app.schemas.ai_analysis import AIAnalysisSchema, AnalysisCreateSchema, AIInsightSchema

router = APIRouter(prefix="/ai", tags=["ai_analyses"])


@router.post("/analyze", response_model=AIAnalysisSchema)
async def analyze_segment(
    analysis_data: AnalysisCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Solicita análise de um segmento."""
    segment = MediaSegmentService.get_segment_by_id(db, analysis_data.segment_id)
    
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento não encontrado"
        )
    
    # Criar análise para cada tipo solicitado
    analyses = []
    for analysis_type in analysis_data.analysis_types:
        analysis = AIAnalysisService.create_analysis(
            db,
            segment_id=analysis_data.segment_id,
            channel_id=segment.channel_id,
            analysis_type=analysis_type,
            created_by=UUID(current_user["user_id"])
        )
        analyses.append(analysis)
    
    # Retornar a primeira análise (ou agregada)
    return analyses[0] if analyses else None


@router.get("/analyses/{analysis_id}", response_model=AIAnalysisSchema)
async def get_analysis(
    analysis_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém resultado da análise."""
    analysis = AIAnalysisService.get_analysis_by_id(db, analysis_id)
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Análise não encontrada"
        )
    
    return analysis


@router.post("/analyses/{analysis_id}/cancel")
async def cancel_analysis(
    analysis_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancela análise em andamento."""
    analysis = AIAnalysisService.get_analysis_by_id(db, analysis_id)
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Análise não encontrada"
        )
    
    if analysis.status != "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Análise não está em processamento"
        )
    
    updated_analysis = AIAnalysisService.update_analysis(db, analysis_id, status="failed")
    
    return {"success": True}


@router.get("/insights", response_model=list[AIInsightSchema])
async def list_insights(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    channel_id: UUID = Query(None),
    severity: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista insights de IA."""
    insights = AIAnalysisService.get_all_insights(
        db, skip=skip, limit=limit, channel_id=channel_id, severity=severity
    )
    return insights


@router.get("/insights/{insight_id}", response_model=AIInsightSchema)
async def get_insight(
    insight_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um insight específico."""
    insight = AIAnalysisService.get_insight_by_id(db, insight_id)
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight não encontrado"
        )
    
    return insight


@router.post("/insights/{insight_id}/read", response_model=AIInsightSchema)
async def mark_insight_read(
    insight_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marca insight como lido."""
    insight = AIAnalysisService.mark_insight_as_read(db, insight_id)
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight não encontrado"
        )
    
    return insight


@router.post("/quick-analysis")
async def quick_analysis(
    channel_id: UUID,
    duration_seconds: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Análise rápida em tempo real."""
    if duration_seconds < 10 or duration_seconds > 60:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duração deve estar entre 10 e 60 segundos"
        )
    
    # Implementação simplificada
    return {"analysis_id": str(UUID(int=0))}
