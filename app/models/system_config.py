"""
Modelo SystemConfig para gerenciar configurações do sistema.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from app.core.database import Base


class SystemConfig(Base):
    """Modelo de configuração do sistema."""
    __tablename__ = "system_config"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSONB)
    description = Column(Text)
    updated_at = Column(DateTime)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
