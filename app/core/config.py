"""
Configurações da aplicação FastAPI.
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configurações gerais da aplicação."""
    
    # Banco de dados
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/broadcast_db"
    )
    
    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # API
    api_title: str = os.getenv("API_TITLE", "Broadcast Streaming API")
    api_version: str = os.getenv("API_VERSION", "1.0.0")
    api_description: str = os.getenv(
        "API_DESCRIPTION",
        "API FastAPI para Sistema de Ingestão de Streams Broadcast"
    )
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
