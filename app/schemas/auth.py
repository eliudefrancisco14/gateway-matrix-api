"""
Schemas Pydantic para autenticação.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID


# class LoginSchema(BaseModel):
#     """Schema para login."""
#     email: str
#     password: str


class TokenSchema(BaseModel):
    """Schema de resposta de token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):
    """Schema para refresh de token."""
    refresh_token: str



class LoginSchema(BaseModel):
    """Schema para login."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=72)  # ← LIMITE 72 BYTES
    

class RegisterSchema(BaseModel):
    """Schema para registro."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=72)  # ← LIMITE 72 BYTES
    name: str = Field(..., min_length=2, max_length=255)
    
    