"""
Configuração do APScheduler para tarefas em background.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Gerenciador central do APScheduler."""
    
    _instance: Optional[AsyncIOScheduler] = None
    
    @classmethod
    def get_scheduler(cls) -> AsyncIOScheduler:
        """Retorna a instância singleton do scheduler."""
        if cls._instance is None:
            jobstores = {
                'default': MemoryJobStore()
            }
            executors = {
                'default': ThreadPoolExecutor(max_workers=10)
            }
            job_defaults = {
                'coalesce': False,
                'max_instances': 3,
                'misfire_grace_time': 30
            }
            
            cls._instance = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            logger.info("APScheduler inicializado")
        
        return cls._instance
    
    @classmethod
    def start(cls):
        """Inicia o scheduler."""
        scheduler = cls.get_scheduler()
        if not scheduler.running:
            scheduler.start()
            logger.info("APScheduler iniciado")
    
    @classmethod
    def shutdown(cls):
        """Para o scheduler."""
        if cls._instance and cls._instance.running:
            cls._instance.shutdown()
            logger.info("APScheduler parado")


# Instância global para importação direta
scheduler = SchedulerManager.get_scheduler()