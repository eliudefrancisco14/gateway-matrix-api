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
    
    @validator('password')
    def validate_password_length(cls, v):
        """Valida que a senha não ultrapassa 72 bytes."""
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Senha não pode ter mais de 72 caracteres (72 bytes)')
        return v
    
    class Config:
        example = {
            "email": "user@example.com",
            "password": "senha_segura_123"
        }


class RegisterSchema(BaseModel):
    """Schema para registro."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=72)  # ← LIMITE 72 BYTES
    name: str = Field(..., min_length=2, max_length=255)
    
    @validator('password')
    def validate_password_length(cls, v):
        """Valida que a senha não ultrapassa 72 bytes."""
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Senha não pode ter mais de 72 caracteres (72 bytes)')
        return v
    
    class Config:
        example = {
            "email": "newuser@example.com",
            "password": "senha_segura_123",
            "name": "João Silva"
        }