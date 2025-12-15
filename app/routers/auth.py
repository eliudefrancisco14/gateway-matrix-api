"""
Rotas de autenticação com tratamento de erros melhorado.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, get_current_user
)
from app.services.user_service import UserService
from app.schemas.auth import LoginSchema, TokenSchema, RefreshTokenSchema, RegisterSchema
from app.schemas.user import UserSchema
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(credentials: RegisterSchema, db: Session = Depends(get_db)):
    """
    Cria um novo utilizador.
    
    Validações:
    - Email deve ser único
    - Senha deve ter entre 6 e 72 caracteres
    """
    # Verificar se email já existe
    existing_user = UserService.get_user_by_email(db, credentials.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registado"
        )
    
    try:
        # Criar utilizador com role viewer por padrão
        user = UserService.create_user(
            db,
            email=credentials.email,
            password=credentials.password,
            name=credentials.name,
            role="viewer"
        )
        return user
    
    except ValueError as e:
        # Capturar erros de validação de senha
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenSchema)
async def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    """
    Autentica um utilizador e retorna tokens JWT.
    
    Retorna:
    - access_token: Token JWT para autenticação
    - refresh_token: Token para renovar access_token
    - token_type: Tipo de token (bearer)
    """
    try:
        user = UserService.authenticate_user(db, credentials.email, credentials.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha inválidos"
            )
        
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    except ValueError as e:
        # Capturar erros de validação de senha
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )


@router.post("/refresh", response_model=TokenSchema)
async def refresh(request: RefreshTokenSchema, db: Session = Depends(get_db)):
    """Renova o token de acesso usando o refresh token."""
    payload = decode_token(request.refresh_token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "refresh_token": request.refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Faz logout do utilizador (invalidar tokens no cliente)."""
    return {"success": True, "message": "Logout realizado com sucesso"}


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtém os dados do utilizador autenticado."""
    from uuid import UUID
    user = UserService.get_user_by_id(db, UUID(current_user["user_id"]))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado"
        )
    
    return user

