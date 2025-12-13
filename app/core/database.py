"""
Configuração da conexão com o banco de dados PostgreSQL.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Criar engine do SQLAlchemy
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20
)

# Criar factory de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency para obter uma sessão do banco de dados.
    Uso: Injetar em endpoints com `db: Session = Depends(get_db)`
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
