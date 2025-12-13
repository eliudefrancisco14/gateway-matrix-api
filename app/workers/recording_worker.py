"""
Recording Worker - Gerencia gravações contínuas e sob demanda.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.channel import Channel
from app.models.recording import Recording
from app.services.recording_service import RecordingService
from app.services.channel_service import ChannelService
from app.utils.ffmpeg_wrapper import FFmpegWrapper
from app.utils.storage_manager import storage_manager

logger = logging.getLogger(__name__)


class RecordingWorker:
    """Worker para gerenciamento de gravações."""
    
    def __init__(self):
        self.running = False
        self.check_interval = 30  # segundos
        self.active_recordings: Dict[str, FFmpegWrapper] = {}
    
    async def start(self):
        """Inicia o worker de gravações."""
        self.running = True
        logger.info("RecordingWorker iniciado")
        
        while self.running:
            try:
                await self._recording_cycle()
                await asyncio.sleep(self.check_interval)
            
            except Exception as e:
                logger.error(f"Erro no cycle de gravação: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Para o worker."""
        self.running = False
        logger.info("RecordingWorker parado")
    
    async def _recording_cycle(self):
        """Executa um ciclo de verificação de gravações."""
        db = SessionLocal()
        
        try:
            # 1. Verificar canais com recording_enabled=True e status=live
            channels = db.query(Channel).filter(
                Channel.recording_enabled == True,
                Channel.status == "live",
                Channel.is_active == True
            ).all()
            
            for channel in channels:
                await self._ensure_recording(db, channel)
            
            # 2. Verificar gravações ativas que devem ser paradas
            active_recordings = db.query(Recording).filter(
                Recording.status == "recording"
            ).all()
            
            for recording in active_recordings:
                channel = ChannelService.get_channel_by_id(db, recording.channel_id)
                
                # Se canal não está mais live, parar gravação
                if not channel or channel.status != "live":
                    await self._stop_recording(db, recording)
        
        finally:
            db.close()
    
    async def _ensure_recording(self, db: Session, channel: Channel):
        """Garante que um canal está sendo gravado."""
        channel_id = str(channel.id)
        
        # Verificar se já existe gravação ativa
        active_recording = db.query(Recording).filter(
            Recording.channel_id == channel.id,
            Recording.status == "recording"
        ).first()
        
        if active_recording:
            # Já está gravando
            logger.debug(f"Canal {channel.name} já está sendo gravado")
            return
        
        # Iniciar nova gravação
        try:
            await self._start_recording(db, channel)
        
        except Exception as e:
            logger.error(f"Erro ao iniciar gravação do canal {channel.name}: {e}")
    
    async def _start_recording(self, db: Session, channel: Channel):
        """Inicia gravação de um canal."""
        channel_id = str(channel.id)
        
        # Criar registro de gravação
        recording = RecordingService.create_recording(
            db,
            channel_id=channel.id,
            format="mp4",
            status="recording"
        )
        
        recording_id = str(recording.id)
        
        # Determinar caminho de saída
        output_dir = storage_manager.get_recording_path(channel.slug, recording_id)
        output_file = str(output_dir / "recording.mp4")
        
        # Atualizar file_path no registro
        RecordingService.update_recording(db, recording.id, file_path=output_file)
        
        # Obter source do canal
        if not channel.source_id:
            logger.error(f"Canal {channel.name} não tem source associada")
            RecordingService.update_recording(db, recording.id, status="failed")
            return
        
        from app.services.source_service import SourceService
        source = SourceService.get_source_by_id(db, channel.source_id)
        
        if not source:
            logger.error(f"Source não encontrada para canal {channel.name}")
            RecordingService.update_recording(db, recording.id, status="failed")
            return
        
        # Iniciar FFmpeg para gravação
        ffmpeg_rec = FFmpegWrapper()
        
        try:
            # Comando FFmpeg para gravação contínua
            cmd = [
                "ffmpeg",
                "-y",
                "-i", source.endpoint_url,
                "-c", "copy",  # Copy codecs (sem transcodificação)
                "-f", "mp4",
                "-movflags", "+faststart",
                output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Armazenar referência
            self.active_recordings[recording_id] = {
                "process": process,
                "ffmpeg": ffmpeg_rec,
                "recording_id": recording.id,
                "channel_id": channel.id
            }
            
            logger.info(f"Gravação iniciada: {channel.name} -> {output_file}")
            
            # Monitorar processo em background
            asyncio.create_task(self._monitor_recording(db, recording.id, process))
        
        except Exception as e:
            logger.error(f"Erro ao iniciar processo de gravação: {e}")
            RecordingService.update_recording(db, recording.id, status="failed")
    
    async def _monitor_recording(self, db: Session, recording_id, process):
        """Monitora o processo de gravação."""
        try:
            await process.wait()
            
            # Processo terminou
            logger.info(f"Processo de gravação terminou: {recording_id}")
            
            # Atualizar status
            recording = RecordingService.get_recording_by_id(db, recording_id)
            if recording and recording.status == "recording":
                RecordingService.stop_recording(db, recording_id)
        
        except Exception as e:
            logger.error(f"Erro ao monitorar gravação: {e}")
    
    async def _stop_recording(self, db: Session, recording: Recording):
        """Para uma gravação ativa."""
        recording_id = str(recording.id)
        
        if recording_id in self.active_recordings:
            rec_info = self.active_recordings[recording_id]
            process = rec_info["process"]
            
            try:
                # Enviar SIGTERM para parar graciosamente
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=10)
                
                logger.info(f"Gravação parada: {recording_id}")
            
            except asyncio.TimeoutError:
                # Forçar kill
                process.kill()
                await process.wait()
                logger.warning(f"Gravação forçada a parar: {recording_id}")
            
            # Remover da lista ativa
            del self.active_recordings[recording_id]
        
        # Atualizar status no BD
        RecordingService.stop_recording(db, recording.id)
        
        # Calcular tamanho do ficheiro
        if recording.file_path:
            file_info = storage_manager.get_file_info(recording.file_path)
            if file_info:
                RecordingService.update_recording(
                    db,
                    recording.id,
                    file_size_bytes=file_info["size_bytes"]
                )
    
    async def start_manual_recording(self, db: Session, channel_id) -> Recording:
        """Inicia gravação manual de um canal."""
        channel = ChannelService.get_channel_by_id(db, channel_id)
        
        if not channel:
            raise ValueError("Canal não encontrado")
        
        if channel.status != "live":
            raise ValueError("Canal não está live")
        
        # Verificar se já está gravando
        active = db.query(Recording).filter(
            Recording.channel_id == channel_id,
            Recording.status == "recording"
        ).first()
        
        if active:
            raise ValueError("Canal já está sendo gravado")
        
        # Iniciar gravação
        await self._start_recording(db, channel)
        
        # Retornar o registro criado
        return db.query(Recording).filter(
            Recording.channel_id == channel_id,
            Recording.status == "recording"
        ).first()
    
    async def stop_manual_recording(self, db: Session, recording_id) -> bool:
        """Para gravação manual."""
        recording = RecordingService.get_recording_by_id(db, recording_id)
        
        if not recording:
            return False
        
        if recording.status != "recording":
            return False
        
        await self._stop_recording(db, recording)
        return True


# Instância global
recording_worker = RecordingWorker()