from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoriaBase(BaseModel):
    """Schema base para Categoria"""
    nome: str = Field(..., min_length=1, max_length=100, description="Nome da categoria")
    descricao: Optional[str] = Field(None, description="Descrição detalhada")
    codigo: Optional[str] = Field(None, max_length=20, description="Código interno")
    categoria_pai_id: Optional[int] = Field(None, description="ID da categoria pai (para subcategorias)")


class CategoriaCreate(CategoriaBase):
    """Schema para criação de categoria"""
    pass


class CategoriaUpdate(BaseModel):
    """Schema para atualização de categoria (campos opcionais)"""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = None
    codigo: Optional[str] = Field(None, max_length=20)
    categoria_pai_id: Optional[int] = None


class CategoriaResponse(CategoriaBase):
    """Schema para resposta da API"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (antes era orm_mode = True)


class CategoriaListResponse(BaseModel):
    """Schema para listagem paginada"""
    total: int
    items: list[CategoriaResponse]
