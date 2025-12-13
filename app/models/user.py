"""
Modelo User para gerenciar utilizadores do sistema.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    """Enum de roles de utilizador."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    """Modelo de utilizador."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    avatar_url = Column(Text)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)
    preferences = Column(JSONB)
