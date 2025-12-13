"""
Aplicação FastAPI principal para Sistema de Ingestão de Streams Broadcast.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.routers import auth, users, sources, channels, recordings, media_segments, ai_analyses, monitoring

# Criar as tabelas no banco de dados
Base.metadata.create_all(bind=engine)

# Criar aplicação FastAPI
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sources.router)
app.include_router(channels.router)
app.include_router(recordings.router)
app.include_router(media_segments.router)
app.include_router(ai_analyses.router)
app.include_router(monitoring.router)


@app.get("/")
async def root():
    """Endpoint raiz da API."""
    return {
        "message": "Bem-vindo à Broadcast Streaming API",
        "version": settings.api_version,
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


@app.get("/health")
async def health_check():
    """Health check da API."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
