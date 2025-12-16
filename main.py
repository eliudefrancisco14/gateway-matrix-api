"""
Aplicação FastAPI principal para Sistema de Ingestão de Streams Broadcast.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from app.core.config import settings
from app.core.database import Base, engine
from app.core.scheduler import SchedulerManager
from app.routers import auth, users, sources, channels, recordings, media_segments, ai_analyses, monitoring, streaming, alerts
from app.workers.source_monitor_worker import source_monitor_worker
from app.workers.recording_worker import recording_worker
from app.workers.alert_worker import alert_worker
from app.utils.ffmpeg_wrapper import ffmpeg_wrapper

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Inicia workers em background no startup e para no shutdown.
    """
    # Startup
    logger.info("Iniciando aplicação...")
    
    # Criar tabelas no banco de dados
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas do banco de dados criadas/verificadas")
    
    # Iniciar scheduler
    SchedulerManager.start()
    
    # Iniciar workers em background
    worker_tasks = [
        asyncio.create_task(source_monitor_worker.start()),
        asyncio.create_task(recording_worker.start()),
        asyncio.create_task(alert_worker.start())
    ]
    
    logger.info("Workers iniciados")
    
    yield
    
    # Shutdown
    logger.info("Parando aplicação...")
    
    # Parar workers
    source_monitor_worker.stop()
    recording_worker.stop()
    alert_worker.stop()
    
    # Aguardar tasks finalizarem
    for task in worker_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Parar todos os processos FFmpeg
    await ffmpeg_wrapper.shutdown_all()
    
    # Parar scheduler
    SchedulerManager.shutdown()
    
    logger.info("Aplicação parada")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan
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
app.include_router(streaming.router)
app.include_router(alerts.router)


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
    return {
        "status": "ok",
        "workers": {
            "source_monitor": source_monitor_worker.running,
            "recording": recording_worker.running,
            "alert": alert_worker.running
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )