"""
Serviço de canais de transmissão.
"""
from sqlalchemy.orm import Session
from app.models.channel import Channel, ChannelEvent
from uuid import UUID
from typing import Optional, List
from datetime import datetime


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
        return channel
    
    @staticmethod
    def delete_channel(db: Session, channel_id: UUID) -> bool:
        """Remove um canal."""
        channel = ChannelService.get_channel_by_id(db, channel_id)
        if channel:
            db.delete(channel)
            db.commit()
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
