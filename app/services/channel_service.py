"""
Serviço de canais de transmissão (modificado com integração ao pipeline).
"""
from sqlalchemy.orm import Session
from app.models.channel import Channel, ChannelEvent
from uuid import UUID
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChannelService:
    """Serviço para gerenciar canais de transmissão."""
    
    @staticmethod
    def create_channel(db: Session, name: str, slug: str, output_format: str,
                      created_by: UUID, **kwargs) -> Channel:
        """Cria um novo canal."""
        channel = Channel(
            name=name,
            slug=slug,
            output_format=output_format,
            created_by=created_by,
            status="offline",
            **kwargs
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        
        logger.info(f"Canal criado: {name} (Slug: {slug})")
        return channel
    
    @staticmethod
    def get_channel_by_id(db: Session, channel_id: UUID) -> Optional[Channel]:
        """Obtém um canal pelo ID."""
        return db.query(Channel).filter(Channel.id == channel_id).first()
    
    @staticmethod
    def get_channel_by_slug(db: Session, slug: str) -> Optional[Channel]:
        """Obtém um canal pelo slug."""
        return db.query(Channel).filter(Channel.slug == slug).first()
    
    @staticmethod
    def get_all_channels(db: Session, skip: int = 0, limit: int = 10,
                        status: Optional[str] = None, category: Optional[str] = None) -> List[Channel]:
        """Obtém todos os canais com paginação e filtros."""
        query = db.query(Channel)
        
        if status:
            query = query.filter(Channel.status == status)
        if category:
            query = query.filter(Channel.category == category)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_channel(db: Session, channel_id: UUID, **kwargs) -> Optional[Channel]:
        """Atualiza um canal."""
        channel = ChannelService.get_channel_by_id(db, channel_id)
        if channel:
            for key, value in kwargs.items():
                if value is not None and hasattr(channel, key):
                    setattr(channel, key, value)
            channel.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(channel)
            logger.info(f"Canal atualizado: {channel.name}")
        return channel
    
    @staticmethod
    def delete_channel(db: Session, channel_id: UUID) -> bool:
        """Remove um canal."""
        channel = ChannelService.get_channel_by_id(db, channel_id)
        if channel:
            db.delete(channel)
            db.commit()
            logger.info(f"Canal removido: {channel.name}")
            return True
        return False
    
    @staticmethod
    def add_event(db: Session, channel_id: UUID, event_type: str, triggered_by: str,
                 details: Optional[dict] = None, user_id: Optional[UUID] = None) -> ChannelEvent:
        """Adiciona um evento a um canal."""
        event = ChannelEvent(
            channel_id=channel_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            triggered_by=triggered_by,
            details=details,
            user_id=user_id
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    
    @staticmethod
    def get_events(db: Session, channel_id: UUID, limit: int = 100) -> List[ChannelEvent]:
        """Obtém os eventos de um canal."""
        return db.query(ChannelEvent).filter(ChannelEvent.channel_id == channel_id).order_by(
            ChannelEvent.timestamp.desc()
        ).limit(limit).all()
    
    @staticmethod
    async def start_channel(db: Session, channel_id: UUID, user_id: Optional[UUID] = None) -> dict:
        """
        Inicia transmissão de um canal.
        
        Returns:
            Dict com status e stream_url
        """
        from app.utils.storage_manager import storage_manager
        from app.utils.ffmpeg_wrapper import ffmpeg_wrapper
        from app.services.source_service import SourceService
        
        channel = ChannelService.get_channel_by_id(db, channel_id)
        
        if not channel:
            raise ValueError("Canal não encontrado")
        
        if not channel.source_id:
            raise ValueError("Canal não tem fonte associada")
        
        # Verificar se fonte está online
        source = SourceService.get_source_by_id(db, channel.source_id)
        
        if not source:
            raise ValueError("Fonte não encontrada")
        
        if source.status != "online":
            raise ValueError(f"Fonte não está online (status: {source.status})")
        
        # Determinar caminho HLS
        hls_path = str(storage_manager.get_hls_output_path(channel.slug))
        
        try:
            # Iniciar ingestão FFmpeg para este canal
            await ffmpeg_wrapper.start_ingest(
                source_id=f"channel_{channel.id}",
                protocol=source.protocol,
                endpoint_url=source.endpoint_url,
                output_path=hls_path,
                output_format=channel.output_format,
                connection_params=source.connection_params,
                transcoding_profile=channel.transcoding_profile
            )
            
            # Atualizar status
            ChannelService.update_channel(db, channel_id, status="live")
            
            # Adicionar evento
            ChannelService.add_event(
                db,
                channel_id,
                event_type="started",
                triggered_by="user" if user_id else "system",
                user_id=user_id
            )
            
            logger.info(f"Canal iniciado: {channel.name}")
            
            return {
                "status": "live",
                "stream_url": f"/stream/{channel.slug}/manifest.m3u8",
                "hls_path": hls_path
            }
        
        except Exception as e:
            logger.error(f"Erro ao iniciar canal: {e}")
            ChannelService.update_channel(db, channel_id, status="error")
            raise
    
    @staticmethod
    async def stop_channel(db: Session, channel_id: UUID, user_id: Optional[UUID] = None) -> bool:
        """
        Para transmissão de um canal.
        
        Returns:
            True se parou com sucesso
        """
        from app.utils.ffmpeg_wrapper import ffmpeg_wrapper
        
        channel = ChannelService.get_channel_by_id(db, channel_id)
        
        if not channel:
            return False
        
        try:
            # Parar ingestão FFmpeg
            await ffmpeg_wrapper.stop_ingest(f"channel_{channel.id}")
            
            # Atualizar status
            ChannelService.update_channel(db, channel_id, status="offline")
            
            # Adicionar evento
            ChannelService.add_event(
                db,
                channel_id,
                event_type="stopped",
                triggered_by="user" if user_id else "system",
                user_id=user_id
            )
            
            logger.info(f"Canal parado: {channel.name}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao parar canal: {e}")
            return False
    
    @staticmethod
    async def switch_source(
        db: Session,
        channel_id: UUID,
        new_source_id: UUID,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Troca a fonte de um canal (failover).
        
        Returns:
            True se trocou com sucesso
        """
        from app.services.source_service import SourceService
        
        channel = ChannelService.get_channel_by_id(db, channel_id)
        
        if not channel:
            return False
        
        # Verificar nova fonte
        new_source = SourceService.get_source_by_id(db, new_source_id)
        
        if not new_source or new_source.status != "online":
            logger.error(f"Nova fonte não está disponível: {new_source_id}")
            return False
        
        old_source_id = channel.source_id
        
        try:
            # Se canal está live, parar e reiniciar com nova fonte
            if channel.status == "live":
                await ChannelService.stop_channel(db, channel_id)
                
                # Atualizar fonte
                ChannelService.update_channel(db, channel_id, source_id=new_source_id)
                
                # Reiniciar
                await ChannelService.start_channel(db, channel_id, user_id)
            else:
                # Apenas atualizar fonte
                ChannelService.update_channel(db, channel_id, source_id=new_source_id)
            
            # Adicionar evento
            ChannelService.add_event(
                db,
                channel_id,
                event_type="source_changed",
                triggered_by="user" if user_id else "failover_rule",
                details={
                    "old_source_id": str(old_source_id),
                    "new_source_id": str(new_source_id)
                },
                user_id=user_id
            )
            
            logger.info(f"Fonte do canal {channel.name} trocada: {old_source_id} -> {new_source_id}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao trocar fonte: {e}")
            return False
    
    @staticmethod
    async def update_thumbnail(db: Session, channel_id: UUID) -> Optional[str]:
        """
        Atualiza o thumbnail de um canal (captura frame atual).
        
        Returns:
            URL do thumbnail ou None
        """
        from app.utils.stream_probe import stream_probe
        from app.utils.storage_manager import storage_manager
        from app.services.source_service import SourceService
        
        channel = ChannelService.get_channel_by_id(db, channel_id)
        
        if not channel or channel.status != "live":
            return None
        
        if not channel.source_id:
            return None
        
        source = SourceService.get_source_by_id(db, channel.source_id)
        
        if not source:
            return None
        
        try:
            # Caminho do thumbnail
            thumb_dir = storage_manager.get_thumbnail_path(channel.slug)
            thumb_path = str(thumb_dir / "current.jpg")
            
            # Capturar snapshot
            success = await stream_probe.get_snapshot(
                source.endpoint_url,
                thumb_path,
                source.protocol
            )
            
            if success:
                # Atualizar no banco
                thumbnail_url = f"/thumbnails/{channel.slug}/current.jpg"
                ChannelService.update_channel(
                    db,
                    channel_id,
                    thumbnail_url=thumbnail_url,
                    thumbnail_updated_at=datetime.utcnow()
                )
                
                return thumbnail_url
            
            return None
        
        except Exception as e:
            logger.error(f"Erro ao atualizar thumbnail: {e}")
            return None
    
    @staticmethod
    def get_channel_status_summary(db: Session) -> dict:
        """
        Retorna resumo de status de todos os canais.
        
        Returns:
            Dict com contagem por status
        """
        from sqlalchemy import func
        
        result = db.query(
            Channel.status,
            func.count(Channel.id).label('count')
        ).filter(
            Channel.is_active == True
        ).group_by(Channel.status).all()
        
        summary = {status: 0 for status in ["live", "offline", "scheduled", "error", "maintenance"]}
        
        for status, count in result:
            summary[status] = count
        
        return summary