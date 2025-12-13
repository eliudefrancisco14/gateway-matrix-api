"""
Schemas Pydantic para utilizadores.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserSchema(BaseModel):
    """Schema de utilizador (resposta)."""
    id: UUID
    email: str
    name: str
    role: str
    avatar_url: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserCreateSchema(BaseModel):
    """Schema para criar utilizador."""
    email: str
    password: str
    name: str
    role: str = "viewer"


class UserUpdateSchema(BaseModel):
    """Schema para atualizar utilizador."""
    name: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
