"""
Serviço de gravações (modificado com lógica de DVR).
"""
from sqlalchemy.orm import Session
from app.models.recording import Recording
from uuid import UUID
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RecordingService:
    """Serviço para gerenciar gravações."""
    
    @staticmethod
    def create_recording(db: Session, channel_id: UUID, **kwargs) -> Recording:
        """Cria uma nova gravação."""
        recording = Recording(
            channel_id=channel_id,
            started_at=datetime.utcnow(),
            status="recording",
            **kwargs
        )
        db.add(recording)
        db.commit()
        db.refresh(recording)
        
        logger.info(f"Gravação criada para canal {channel_id}")
        return recording
    
    @staticmethod
    def get_recording_by_id(db: Session, recording_id: UUID) -> Optional[Recording]:
        """Obtém uma gravação pelo ID."""
        return db.query(Recording).filter(Recording.id == recording_id).first()
    
    @staticmethod
    def get_all_recordings(db: Session, skip: int = 0, limit: int = 10,
                          channel_id: Optional[UUID] = None, status: Optional[str] = None) -> List[Recording]:
        """Obtém todas as gravações com paginação e filtros."""
        query = db.query(Recording)
        
        if channel_id:
            query = query.filter(Recording.channel_id == channel_id)
        if status:
            query = query.filter(Recording.status == status)
        
        return query.order_by(Recording.started_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_recording(db: Session, recording_id: UUID, **kwargs) -> Optional[Recording]:
        """Atualiza uma gravação."""
        recording = RecordingService.get_recording_by_id(db, recording_id)
        if recording:
            for key, value in kwargs.items():
                if value is not None and hasattr(recording, key):
                    setattr(recording, key, value)
            db.commit()
            db.refresh(recording)
        return recording
    
    @staticmethod
    def stop_recording(db: Session, recording_id: UUID) -> Optional[Recording]:
        """Para uma gravação."""
        recording = RecordingService.get_recording_by_id(db, recording_id)
        if recording:
            recording.ended_at = datetime.utcnow()
            recording.status = "completed"
            if recording.started_at:
                recording.duration_seconds = int((recording.ended_at - recording.started_at).total_seconds())
            db.commit()
            db.refresh(recording)
            logger.info(f"Gravação parada: {recording_id}")
        return recording
    
    @staticmethod
    def delete_recording(db: Session, recording_id: UUID) -> bool:
        """Remove uma gravação."""
        from app.utils.storage_manager import storage_manager
        import asyncio
        
        recording = RecordingService.get_recording_by_id(db, recording_id)
        if recording:
            # Remover ficheiro se existir
            if recording.file_path:
                asyncio.create_task(storage_manager.delete_file(recording.file_path))
            
            db.delete(recording)
            db.commit()
            logger.info(f"Gravação removida: {recording_id}")
            return True
        return False
    
    @staticmethod
    def get_download_url(recording_id: UUID) -> str:
        """
        Retorna URL de download para uma gravação.
        
        Returns:
            URL relativa para download
        """
        return f"/recordings/{recording_id}/download"
    
    @staticmethod
    def get_playback_url(recording_id: UUID) -> str:
        """
        Retorna URL de playback para uma gravação.
        
        Returns:
            URL relativa para reprodução
        """
        return f"/recordings/{recording_id}/play"
    
    @staticmethod
    async def export_recording(
        db: Session,
        recording_id: UUID,
        export_format: str = "mp4"
    ) -> Optional[str]:
        """
        Exporta gravação para formato específico.
        
        Args:
            recording_id: ID da gravação
            export_format: Formato de exportação (mp4, mov, mkv)
        
        Returns:
            Caminho do ficheiro exportado ou None
        """
        from app.utils.storage_manager import storage_manager
        import asyncio
        
        recording = RecordingService.get_recording_by_id(db, recording_id)
        
        if not recording or not recording.file_path:
            return None
        
        try:
            # Determinar caminho de saída
            from pathlib import Path
            source_path = Path(recording.file_path)
            export_path = source_path.parent / f"export_{recording_id}.{export_format}"
            
            # Se formato é o mesmo, apenas copiar
            if recording.format == export_format:
                await storage_manager.save_file(str(source_path), str(export_path))
                return str(export_path)
            
            # Caso contrário, usar FFmpeg para converter
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(source_path),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-f", export_format,
                str(export_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0:
                logger.info(f"Gravação exportada: {recording_id} -> {export_format}")
                return str(export_path)
            else:
                logger.error(f"Erro ao exportar gravação: {recording_id}")
                return None
        
        except Exception as e:
            logger.error(f"Erro ao exportar gravação: {e}")
            return None
    
    @staticmethod
    def get_recordings_summary(db: Session, channel_id: Optional[UUID] = None) -> dict:
        """
        Retorna resumo de gravações.
        
        Args:
            channel_id: Filtrar por canal (opcional)
        
        Returns:
            Dict com estatísticas
        """
        from sqlalchemy import func
        
        query = db.query(Recording)
        
        if channel_id:
            query = query.filter(Recording.channel_id == channel_id)
        
        total = query.count()
        recording = query.filter(Recording.status == "recording").count()
        completed = query.filter(Recording.status == "completed").count()
        failed = query.filter(Recording.status == "failed").count()
        
        # Total em GB
        total_size = db.query(
            func.sum(Recording.file_size_bytes)
        ).filter(
            Recording.status == "completed"
        )
        
        if channel_id:
            total_size = total_size.filter(Recording.channel_id == channel_id)
        
        total_size_bytes = total_size.scalar() or 0
        total_size_gb = round(total_size_bytes / (1024**3), 2)
        
        return {
            "total": total,
            "recording": recording,
            "completed": completed,
            "failed": failed,
            "total_size_gb": total_size_gb
        }