"""
Source Monitor Worker - Monitora fontes ativas e atualiza status/métricas.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.source import Source
from app.services.source_service import SourceService
from app.utils.stream_probe import stream_probe
from app.utils.ffmpeg_wrapper import ffmpeg_wrapper

logger = logging.getLogger(__name__)


class SourceMonitorWorker:
    """Worker para monitoramento de fontes."""
    
    def __init__(self):
        self.running = False
        self.monitor_interval = 10  # segundos
        self.probe_interval = 60  # segundos (probe completo)
        self.last_probe: Dict[str, datetime] = {}
    
    async def start(self):
        """Inicia o worker de monitoramento."""
        self.running = True
        logger.info("SourceMonitorWorker iniciado")
        
        while self.running:
            try:
                await self._monitor_cycle()
                await asyncio.sleep(self.monitor_interval)
            
            except Exception as e:
                logger.error(f"Erro no cycle de monitoramento: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Para o worker."""
        self.running = False
        logger.info("SourceMonitorWorker parado")
    
    async def _monitor_cycle(self):
        """Executa um ciclo de monitoramento."""
        db = SessionLocal()
        
        try:
            # Buscar todas as fontes ativas
            sources = db.query(Source).filter(Source.is_active == True).all()
            
            for source in sources:
                await self._monitor_source(db, source)
        
        finally:
            db.close()
    
    async def _monitor_source(self, db: Session, source: Source):
        """Monitora uma fonte específica."""
        source_id = str(source.id)
        
        try:
            # 1. Verificar se o processo FFmpeg está ativo
            is_ffmpeg_running = ffmpeg_wrapper.is_running(source_id)
            
            # 2. Status atual
            current_status = source.status
            
            # 3. Decidir ação baseado no status
            if current_status == "connecting":
                await self._handle_connecting(db, source, is_ffmpeg_running)
            
            elif current_status == "online":
                await self._handle_online(db, source, is_ffmpeg_running)
            
            elif current_status == "offline":
                await self._handle_offline(db, source)
            
            elif current_status == "error":
                await self._handle_error(db, source)
        
        except Exception as e:
            logger.error(f"Erro ao monitorar fonte {source.name}: {e}")
    
    async def _handle_connecting(self, db: Session, source: Source, is_ffmpeg_running: bool):
        """Trata fonte em estado 'connecting'."""
        source_id = str(source.id)
        
        # Se FFmpeg ainda não foi iniciado, tentar iniciar
        if not is_ffmpeg_running:
            await self._start_ingest(db, source)
            return
        
        # Se FFmpeg está rodando, fazer probe para confirmar
        should_probe = self._should_probe(source_id)
        
        if should_probe:
            stream_info = await stream_probe.probe(
                source.endpoint_url,
                source.protocol,
                timeout=5
            )
            
            if stream_info and stream_info.is_valid():
                # Stream válido: marcar como online
                SourceService.update_source(
                    db,
                    source.id,
                    status="online",
                    last_seen_at=datetime.utcnow()
                )
                
                # Adicionar métrica inicial
                SourceService.add_metric(
                    db,
                    source.id,
                    video_codec=stream_info.video_codec,
                    audio_codec=stream_info.audio_codec,
                    resolution=stream_info.resolution,
                    fps=stream_info.fps,
                    bitrate_kbps=stream_info.bitrate // 1000 if stream_info.bitrate else None
                )
                
                logger.info(f"Fonte {source.name} conectada com sucesso")
                self.last_probe[source_id] = datetime.utcnow()
            
            else:
                # Ainda não conseguiu conectar
                # Verificar timeout (ex: 60 segundos)
                if source.created_at and (datetime.utcnow() - source.created_at).seconds > 60:
                    SourceService.update_source(db, source.id, status="error")
                    logger.warning(f"Fonte {source.name} timeout na conexão")
    
    async def _handle_online(self, db: Session, source: Source, is_ffmpeg_running: bool):
        """Trata fonte em estado 'online'."""
        source_id = str(source.id)
        
        # Se FFmpeg parou, marcar como offline
        if not is_ffmpeg_running:
            SourceService.update_source(db, source.id, status="offline")
            logger.warning(f"Fonte {source.name} offline (FFmpeg parou)")
            return
        
        # Probe periódico para coletar métricas
        should_probe = self._should_probe(source_id)
        
        if should_probe:
            stream_info = await stream_probe.probe(
                source.endpoint_url,
                source.protocol,
                timeout=5
            )
            
            if stream_info and stream_info.is_valid():
                # Atualizar last_seen
                SourceService.update_source(
                    db,
                    source.id,
                    last_seen_at=datetime.utcnow()
                )
                
                # Adicionar métrica
                SourceService.add_metric(
                    db,
                    source.id,
                    video_codec=stream_info.video_codec,
                    audio_codec=stream_info.audio_codec,
                    resolution=stream_info.resolution,
                    fps=stream_info.fps,
                    bitrate_kbps=stream_info.bitrate // 1000 if stream_info.bitrate else None
                )
                
                self.last_probe[source_id] = datetime.utcnow()
            
            else:
                # Probe falhou: marcar como unstable
                SourceService.update_source(db, source.id, status="unstable")
                logger.warning(f"Fonte {source.name} instável")
    
    async def _handle_offline(self, db: Session, source: Source):
        """Trata fonte em estado 'offline'."""
        # Fonte offline: não fazer nada (aguardar intervenção manual ou reconexão)
        pass
    
    async def _handle_error(self, db: Session, source: Source):
        """Trata fonte em estado 'error'."""
        # Fonte em erro: aguardar intervenção manual
        pass
    
    async def _start_ingest(self, db: Session, source: Source):
        """Inicia a ingestão de uma fonte."""
        try:
            from app.utils.storage_manager import storage_manager
            
            # Determinar caminho de saída (HLS)
            # Para fontes, usamos um diretório temporário que será usado pelos canais
            output_path = str(storage_manager.get_hls_output_path(f"source_{source.id}"))
            
            # Callback de erro
            async def on_error(error_msg: str):
                logger.error(f"FFmpeg erro [{source.name}]: {error_msg}")
                SourceService.update_source(db, source.id, status="error")
            
            # Iniciar FFmpeg
            await ffmpeg_wrapper.start_ingest(
                source_id=str(source.id),
                protocol=source.protocol,
                endpoint_url=source.endpoint_url,
                output_path=output_path,
                output_format="hls",
                connection_params=source.connection_params,
                on_error=on_error
            )
            
            logger.info(f"Ingestão iniciada para {source.name}")
        
        except Exception as e:
            logger.error(f"Erro ao iniciar ingestão: {e}")
            SourceService.update_source(db, source.id, status="error")
    
    def _should_probe(self, source_id: str) -> bool:
        """Verifica se deve fazer probe agora."""
        if source_id not in self.last_probe:
            return True
        
        elapsed = (datetime.utcnow() - self.last_probe[source_id]).seconds
        return elapsed >= self.probe_interval


# Instância global
source_monitor_worker = SourceMonitorWorker()