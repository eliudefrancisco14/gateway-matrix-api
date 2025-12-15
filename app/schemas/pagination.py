"""
Schemas e utilitários para paginação consistente.
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Parâmetros de paginação padronizados."""
    skip: int = Field(
        default=0,
        ge=0,
        description="Número de registros a pular"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Número máximo de registros por página"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Resposta paginada genérica."""
    items: List[T]
    total: int = Field(..., description="Total de registros (sem paginação)")
    skip: int = Field(..., description="Registros pulados")
    limit: int = Field(..., description="Limite por página")
    page: int = Field(..., description="Página atual (baseado em skip/limit)")
    pages: int = Field(..., description="Total de páginas")
    
    @classmethod
    def create(cls, items: List[T], total: int, skip: int, limit: int):
        """
        Factory method para criar resposta paginada.
        
        Args:
            items: Lista de itens da página atual
            total: Total de registros (sem paginação)
            skip: Número de registros pulados
            limit: Limite de registros por página
        """
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = (total + limit - 1) // limit if limit > 0 else 1
        
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            page=page,
            pages=pages
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 42,
                "skip": 0,
                "limit": 10,
                "page": 1,
                "pages": 5
            }
        }