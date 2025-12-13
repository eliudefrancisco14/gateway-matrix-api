"""
Rotas de utilizadores e administração.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.user_service import UserService
from app.schemas.user import UserSchema, UserCreateSchema, UserUpdateSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserSchema])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role: str = Query(None),
    active: bool = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todos os utilizadores (apenas admin)."""
    # Verificar se é admin
    user = UserService.get_user_by_id(db, UUID(current_user["user_id"]))
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    
    users = UserService.get_all_users(db, skip=skip, limit=limit)
    return users


@router.post("", response_model=UserSchema)
async def create_user(
    user_data: UserCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria um novo utilizador (apenas admin)."""
    # Verificar se é admin
    user = UserService.get_user_by_id(db, UUID(current_user["user_id"]))
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    
    # Verificar se email já existe
    existing_user = UserService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registado"
        )
    
    new_user = UserService.create_user(
        db,
        email=user_data.email,
        password=user_data.password,
        name=user_data.name,
        role=user_data.role
    )
    
    return new_user


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um utilizador específico."""
    user = UserService.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado"
        )
    
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: UUID,
    user_data: UserUpdateSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza um utilizador."""
    # Verificar permissões
    current_user_obj = UserService.get_user_by_id(db, UUID(current_user["user_id"]))
    if not current_user_obj or (current_user_obj.role != "admin" and current_user_obj.id != user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    
    updated_user = UserService.update_user(db, user_id, **user_data.dict(exclude_unset=True))
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado"
        )
    
    return updated_user


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Desativa um utilizador (apenas admin)."""
    # Verificar se é admin
    user = UserService.get_user_by_id(db, UUID(current_user["user_id"]))
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    
    # Não permitir desativar a si mesmo
    if str(user_id) == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não pode desativar a sua própria conta"
        )
    
    success = UserService.delete_user(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado"
        )
    
    return {"success": True}
