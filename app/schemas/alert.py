"""
Schemas Pydantic para alertas.
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class AlertSchema(BaseModel):
    """Schema de alerta (resposta)."""
    id: UUID
    severity: str
    message: str
    source_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    acknowledged: bool
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertCountsSchema(BaseModel):
    """Schema de contagens de alertas."""
    critical: int
    error: int
    warning: int
    info: int
    total: int
    unacknowledged: int