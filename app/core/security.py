"""
Funções de segurança, autenticação e autorização.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Contexto de hash de senhas com configuração otimizada
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Número de rounds (mais seguro)
)

# Esquema de segurança
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash de uma senha usando bcrypt com validação de tamanho.
    
    Args:
        password: Senha em texto plano (máximo 72 bytes)
    
    Returns:
        Hash bcrypt da senha
    
    Raises:
        ValueError: Se a senha exceder 72 bytes
    """
    # Validar tamanho da senha APENAS NA CRIAÇÃO DO HASH
    password_bytes = password.encode('utf-8')
    
    if len(password_bytes) > 72:
        raise ValueError(
            f'Senha não pode ter mais de 72 bytes. '
            f'Tamanho atual: {len(password_bytes)} bytes'
        )
    
    try:
        return pwd_context.hash(password)
    except ValueError as e:
        # Capturar erro específico do bcrypt
        if "password cannot be longer than 72 bytes" in str(e):
            raise ValueError(
                'Senha é muito longa. Máximo 72 caracteres permitidos.'
            )
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha corresponde ao hash.
    
    Args:
        plain_password: Senha em texto plano (do login)
        hashed_password: Hash bcrypt armazenado no banco
    
    Returns:
        True se a senha é válida, False caso contrário
    
    Nota:
        NÃO valida tamanho aqui - bcrypt já trata internamente.
        A validação de 72 bytes é APENAS para hash_password().
    """
    try:
        # Passlib/bcrypt já lida com todas as validações necessárias
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log para debug sem expor detalhes ao usuário
        logger.debug(f"Falha na verificação de senha: {type(e).__name__}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT de acesso."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Cria um token JWT de refresh."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decodifica um token JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency para obter o utilizador autenticado a partir do token JWT."""
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    return {"user_id": user_id}


def require_role(required_role: str):
    """Factory para criar uma dependency que verifica o role do utilizador."""
    async def check_role(current_user: dict = Depends(get_current_user)):
        # Nota: Implementação simplificada. Em produção, buscar o utilizador no BD.
        if current_user.get("role") != required_role and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente"
            )
        return current_user
    
    return check_role