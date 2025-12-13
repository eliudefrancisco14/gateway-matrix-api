"""
Schemas Pydantic para autenticação.
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class LoginSchema(BaseModel):
    """Schema para login."""
    email: str
    password: str


class TokenSchema(BaseModel):
    """Schema de resposta de token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):
    """Schema para refresh de token."""
    refresh_token: str
