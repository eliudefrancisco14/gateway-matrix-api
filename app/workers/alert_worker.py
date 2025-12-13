"""
Alert Worker - Sistema de alertas para monitoramento de fontes e canais.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.source import Source, SourceMetric
from app.models.channel import Channel
from app.services.ai_analysis_service import AIAnalysisService

logger = logging.getLogger(__name__)


class AlertRule:
    """Representa uma regra de alerta."""
    
    def __init__(self, name: str, check_func, severity: str, message_template: str):
        self.name = name
        self.check_func = check_func
        self.severity = severity  # info, warning, critical
        self.message_template = message_template
        self.last_triggered: Dict[str, datetime] = {}
        self.cooldown_seconds = 300  # 5 minutos entre alertas do mesmo tipo
    
    def can_trigger(self, entity_id: str) -> bool:
        """Verifica se pode disparar alerta (cooldown)."""
        if entity_id not in self.last_triggered:
            return True
        
        elapsed = (datetime.utcnow() - self.last_triggered[entity_id]).seconds
        return elapsed >= self.cooldown_seconds
    
    def mark_triggered(self, entity_id: str):
        """Marca que o alerta foi disparado."""
        self.last_triggered[entity_id] = datetime.utcnow()


class AlertWorker:
    """Worker para sistema de alertas."""
    
    def __init__(self):
        self.running = False
        self.check_interval = 30  # segundos
        self.rules: List[AlertRule] = []
        self._setup_rules()
    
    def _setup_rules(self):
        """Configura as regras de alerta."""
        
        # Regra 1: Fonte desconectada
        self.rules.append(AlertRule(
            name="source_disconnected",
            check_func=self._check_source_disconnected,
            severity="critical",
            message_template="Fonte '{name}' desconectou"
        ))
        
        # Regra 2: Bitrate baixo
        self.rules.append(AlertRule(
            name="low_bitrate",
            check_func=self._check_low_bitrate,
            severity="warning",
            message_template="Fonte '{name}' com bitrate baixo: {bitrate} kbps"
        ))
        
        # Regra 3: Packet loss alto
        self.rules.append(AlertRule(
            name="high_packet_loss",
            check_func=self._check_high_packet_loss,
            severity="warning",
            message_template="Fonte '{name}' com packet loss alto: {packet_loss}%"
        ))
        
        # Regra 4: Canal offline inesperadamente
        self.rules.append(AlertRule(
            name="channel_unexpected_offline",
            check_func=self._check_channel_offline,
            severity="critical",
            message_template="Canal '{name}' offline inesperadamente"
        ))
        
        logger.info(f"{len(self.rules)} regras de alerta configuradas")
    
    async def start(self):
        """Inicia o worker de alertas."""
        self.running = True
        logger.info("AlertWorker iniciado")
        
        while self.running:
            try:
                await self._alert_cycle()
                await asyncio.sleep(self.check_interval)
            
            except Exception as e:
                logger.error(f"Erro no cycle de alertas: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Para o worker."""
        self.running = False
        logger.info("AlertWorker parado")
    
    async def _alert_cycle(self):
        """Executa um ciclo de verificação de alertas."""
        db = SessionLocal()
        
        try:
            # Verificar todas as regras
            for rule in self.rules:
                await self._check_rule(db, rule)
        
        finally:
            db.close()
    
    async def _check_rule(self, db: Session, rule: AlertRule):
        """Verifica uma regra de alerta."""
        try:
            alerts = await rule.check_func(db)
            
            for alert in alerts:
                entity_id = alert["entity_id"]
                
                if rule.can_trigger(entity_id):
                    await self._create_alert(db, rule, alert)
                    rule.mark_triggered(entity_id)
        
        except Exception as e:
            logger.error(f"Erro ao verificar regra {rule.name}: {e}")
    
    async def _check_source_disconnected(self, db: Session) -> List[dict]:
        """Verifica fontes desconectadas."""
        alerts = []
        
        # Fontes que estavam online mas agora estão offline/error
        sources = db.query(Source).filter(
            Source.is_active == True,
            Source.status.in_(["offline", "error"])
        ).all()
        
        for source in sources:
            # Verificar se estava online recentemente (última hora)
            if source.last_seen_at:
                elapsed = (datetime.utcnow() - source.last_seen_at).seconds
                if elapsed < 3600:  # 1 hora
                    alerts.append({
                        "entity_id": str(source.id),
                        "entity_type": "source",
                        "name": source.name,
                        "data": {
                            "status": source.status,
                            "last_seen": source.last_seen_at.isoformat() if source.last_seen_at else None
                        }
                    })
        
        return alerts
    
    async def _check_low_bitrate(self, db: Session) -> List[dict]:
        """Verifica bitrate baixo."""
        alerts = []
        threshold_kbps = 500  # Threshold: 500 kbps
        
        sources = db.query(Source).filter(
            Source.is_active == True,
            Source.status == "online"
        ).all()
        
        for source in sources:
            # Obter métrica mais recente
            recent_metric = db.query(SourceMetric).filter(
                SourceMetric.source_id == source.id
            ).order_by(SourceMetric.timestamp.desc()).first()
            
            if recent_metric and recent_metric.bitrate_kbps:
                if recent_metric.bitrate_kbps < threshold_kbps:
                    alerts.append({
                        "entity_id": str(source.id),
                        "entity_type": "source",
                        "name": source.name,
                        "bitrate": recent_metric.bitrate_kbps,
                        "data": {
                            "bitrate_kbps": recent_metric.bitrate_kbps,
                            "threshold_kbps": threshold_kbps
                        }
                    })
        
        return alerts
    
    async def _check_high_packet_loss(self, db: Session) -> List[dict]:
        """Verifica packet loss alto."""
        alerts = []
        threshold_percent = 5.0  # Threshold: 5%
        
        sources = db.query(Source).filter(
            Source.is_active == True,
            Source.status == "online"
        ).all()
        
        for source in sources:
            # Obter métrica mais recente
            recent_metric = db.query(SourceMetric).filter(
                SourceMetric.source_id == source.id
            ).order_by(SourceMetric.timestamp.desc()).first()
            
            if recent_metric and recent_metric.packet_loss_percent:
                if float(recent_metric.packet_loss_percent) > threshold_percent:
                    alerts.append({
                        "entity_id": str(source.id),
                        "entity_type": "source",
                        "name": source.name,
                        "packet_loss": float(recent_metric.packet_loss_percent),
                        "data": {
                            "packet_loss_percent": float(recent_metric.packet_loss_percent),
                            "threshold_percent": threshold_percent
                        }
                    })
        
        return alerts
    
    async def _check_channel_offline(self, db: Session) -> List[dict]:
        """Verifica canais que ficaram offline inesperadamente."""
        alerts = []
        
        # Canais que deveriam estar live mas estão offline
        channels = db.query(Channel).filter(
            Channel.is_active == True,
            Channel.status == "offline"
        ).all()
        
        for channel in channels:
            # Verificar se tem fonte associada online
            if channel.source_id:
                from app.services.source_service import SourceService
                source = SourceService.get_source_by_id(db, channel.source_id)
                
                if source and source.status == "online":
                    # Fonte online mas canal offline: alerta
                    alerts.append({
                        "entity_id": str(channel.id),
                        "entity_type": "channel",
                        "name": channel.name,
                        "data": {
                            "channel_status": channel.status,
                            "source_status": source.status,
                            "source_name": source.name
                        }
                    })
        
        return alerts
    
    async def _create_alert(self, db: Session, rule: AlertRule, alert_data: dict):
        """Cria um insight de alerta."""
        try:
            message = rule.message_template.format(**alert_data)
            
            # Determinar channel_id (se aplicável)
            channel_id = None
            if alert_data["entity_type"] == "channel":
                channel_id = alert_data["entity_id"]
            elif alert_data["entity_type"] == "source":
                # Buscar canais associados a esta fonte
                source_id = alert_data["entity_id"]
                channel = db.query(Channel).filter(
                    Channel.source_id == source_id
                ).first()
                
                if channel:
                    channel_id = channel.id
            
            if not channel_id:
                logger.warning(f"Alerta sem channel_id: {message}")
                return
            
            # Criar insight
            AIAnalysisService.create_insight(
                db,
                channel_id=channel_id,
                insight_type="alert",
                severity=rule.severity,
                title=f"Alerta: {rule.name}",
                description=message,
                is_actionable=True,
                data=alert_data.get("data", {})
            )
            
            logger.info(f"Alerta criado: {message}")
        
        except Exception as e:
            logger.error(f"Erro ao criar alerta: {e}")


# Instância global
alert_worker = AlertWorker()