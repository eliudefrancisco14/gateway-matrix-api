"""
Serviço de utilizadores.
"""
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password, verify_password
from uuid import UUID
from typing import Optional, List


class UserService:
    """Serviço para gerenciar utilizadores."""
    
    @staticmethod
    def create_user(db: Session, email: str, password: str, name: str, role: str = "viewer") -> User:
        """Cria um novo utilizador."""
        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """Obtém um utilizador pelo ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Obtém um utilizador pelo email."""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Autentica um utilizador."""
        user = UserService.get_user_by_email(db, email)
        if user and verify_password(password, user.password_hash):
            return user
        return None
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 10) -> List[User]:
        """Obtém todos os utilizadores com paginação."""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_user(db: Session, user_id: UUID, **kwargs) -> Optional[User]:
        """Atualiza um utilizador."""
        user = UserService.get_user_by_id(db, user_id)
        if user:
            for key, value in kwargs.items():
                if value is not None and hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
        return user
    
    @staticmethod
    def delete_user(db: Session, user_id: UUID) -> bool:
        """Desativa um utilizador."""
        user = UserService.get_user_by_id(db, user_id)
        if user:
            user.is_active = False
            db.commit()
            return True
        return False
