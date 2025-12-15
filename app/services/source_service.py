"""
Serviço de fontes de ingestão (modificado com lógica de conexão real).
"""
from sqlalchemy.orm import Session
from app.models.source import Source, SourceMetric
from uuid import UUID
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SourceService:
    """Serviço para gerenciar fontes de ingestão."""
    
    @staticmethod
    def create_source(db: Session, name: str, protocol: str, source_type: str,
                     endpoint_url: str, created_by: UUID, **kwargs) -> Source:
        """
        Cria uma nova fonte.
        Inicia automaticamente em status 'connecting' - o monitor worker tentará conectar.
        
        Para YouTube: extrai video_id e armazena URL original e stream URL.
        """
        import re
        
        # Processamento especial para YouTube
        if protocol == "youtube":
            # Extrair video_id
            youtube_patterns = [
                r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
                r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([a-zA-Z0-9_-]{11})',
                r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})',
            ]
            
            video_id = None
            for pattern in youtube_patterns:
                match = re.search(pattern, endpoint_url)
                if match:
                    video_id = match.group(1)
                    break
            
            if video_id:
                # Armazenar URL original e video_id em meta_data
                meta_data = kwargs.get('meta_data', {}) or {}
                meta_data['original_url'] = endpoint_url
                meta_data['video_id'] = video_id
                meta_data['stream_url'] = endpoint_url  # Será atualizado pelo worker com URL real do stream
                kwargs['meta_data'] = meta_data
                
                logger.info(f"YouTube video_id extraído: {video_id}")
        
        source = Source(
            name=name,
            protocol=protocol,
            source_type=source_type,
            endpoint_url=endpoint_url,
            created_by=created_by,
            status="connecting",  # Inicia como connecting
            **kwargs
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        
        logger.info(f"Fonte criada: {name} (ID: {source.id}, Status: connecting)")
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
            logger.info(f"Fonte atualizada: {source.name} (ID: {source_id})")
        return source
    
    @staticmethod
    def delete_source(db: Session, source_id: UUID) -> bool:
        """Remove uma fonte."""
        source = SourceService.get_source_by_id(db, source_id)
        if source:
            # Importar aqui para evitar circular import
            from app.utils.ffmpeg_wrapper import ffmpeg_wrapper
            import asyncio
            
            # Parar ingestão se estiver ativa
            if ffmpeg_wrapper.is_running(str(source_id)):
                asyncio.create_task(ffmpeg_wrapper.stop_ingest(str(source_id)))
            
            db.delete(source)
            db.commit()
            logger.info(f"Fonte removida: {source.name} (ID: {source_id})")
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
    
    @staticmethod
    def get_metrics_history(
        db: Session,
        source_id: UUID,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[SourceMetric]:
        """
        Obtém histórico de métricas com filtro de período.
        
        Args:
            source_id: ID da fonte
            from_time: Data/hora inicial (opcional)
            to_time: Data/hora final (opcional)
            limit: Limite de registros
        """
        query = db.query(SourceMetric).filter(SourceMetric.source_id == source_id)
        
        if from_time:
            query = query.filter(SourceMetric.timestamp >= from_time)
        
        if to_time:
            query = query.filter(SourceMetric.timestamp <= to_time)
        
        return query.order_by(SourceMetric.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    async def test_source_connectivity(db: Session, source_id: UUID) -> dict:
        """
        Testa a conectividade de uma fonte usando stream probe.
        
        Returns:
            Dict com resultado do teste
        """
        from app.utils.stream_probe import stream_probe
        
        source = SourceService.get_source_by_id(db, source_id)
        
        if not source:
            return {
                "reachable": False,
                "error": "Fonte não encontrada"
            }
        
        try:
            # Teste rápido de conectividade
            is_reachable = await stream_probe.test_connectivity(
                source.endpoint_url,
                source.protocol,
                timeout=5
            )
            
            if is_reachable:
                # Fazer probe completo
                stream_info = await stream_probe.probe(
                    source.endpoint_url,
                    source.protocol,
                    timeout=10
                )
                
                if stream_info:
                    return {
                        "reachable": True,
                        "stream_info": stream_info.to_dict()
                    }
                else:
                    return {
                        "reachable": True,
                        "message": "Conectado mas probe falhou"
                    }
            else:
                return {
                    "reachable": False,
                    "error": "Não foi possível conectar ao endpoint"
                }
        
        except Exception as e:
            logger.error(f"Erro ao testar conectividade: {e}")
            return {
                "reachable": False,
                "error": str(e)
            }
    
    @staticmethod
    async def reconnect_source(db: Session, source_id: UUID) -> bool:
        """
        Força reconexão de uma fonte.
        
        Returns:
            True se reconexão foi iniciada
        """
        from app.utils.ffmpeg_wrapper import ffmpeg_wrapper
        
        source = SourceService.get_source_by_id(db, source_id)
        
        if not source:
            return False
        
        try:
            # Parar ingestão atual (se existir)
            await ffmpeg_wrapper.stop_ingest(str(source_id))
            
            # Atualizar status para connecting
            SourceService.update_source(db, source_id, status="connecting")
            
            logger.info(f"Reconexão iniciada para fonte: {source.name}")
            
            # O source_monitor_worker detectará o status 'connecting' e iniciará a ingestão
            return True
        
        except Exception as e:
            logger.error(f"Erro ao reconectar fonte: {e}")
            return False
    
    @staticmethod
    def get_source_status_summary(db: Session) -> dict:
        """
        Retorna resumo de status de todas as fontes.
        
        Returns:
            Dict com contagem por status
        """
        from sqlalchemy import func
        
        result = db.query(
            Source.status,
            func.count(Source.id).label('count')
        ).filter(
            Source.is_active == True
        ).group_by(Source.status).all()
        
        summary = {status: 0 for status in ["online", "offline", "connecting", "unstable", "error"]}
        
        for status, count in result:
            summary[status] = count
        
        return summary