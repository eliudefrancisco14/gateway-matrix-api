"""
Módulo routers com as rotas da API.
"""
from app.routers import auth, users, sources, channels, recordings, media_segments, ai_analyses, monitoring

__all__ = ["auth", "users", "sources", "channels", "recordings", "media_segments", "ai_analyses", "monitoring"]
