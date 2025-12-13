"""
Modelo AuditLog para registrar ações do sistema.
"""
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from datetime import datetime
from app.core.database import Base


class AuditLog(Base):
    """Modelo de log de auditoria."""
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True))
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
