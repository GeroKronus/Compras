from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class ProdutoBase(BaseModel):
    """Schema base para Produto"""
    codigo: str = Field(..., min_length=1, max_length=50, description="Código interno do produto")
    nome: str = Field(..., min_length=1, max_length=200, description="Nome do produto")
    descricao: Optional[str] = Field(None, description="Descrição detalhada")
    categoria_id: Optional[int] = Field(None, description="ID da categoria")
    unidade_medida: str = Field("UN", max_length=20, description="Unidade de medida (UN, KG, M, L, etc)")
    estoque_minimo: Optional[Decimal] = Field(0, ge=0, description="Estoque mínimo")
    estoque_maximo: Optional[Decimal] = Field(None, ge=0, description="Estoque máximo")
    preco_referencia: Optional[Decimal] = Field(None, ge=0, description="Preço de referência")
    especificacoes: Optional[Dict[str, Any]] = Field(None, description="Especificações técnicas (JSON)")
    imagem_url: Optional[str] = Field(None, max_length=500, description="URL da imagem")
    ativo: bool = Field(True, description="Produto ativo")
    observacoes: Optional[str] = Field(None, description="Observações gerais")

    @field_validator('estoque_maximo')
    @classmethod
    def validar_estoque_maximo(cls, v, info):
        """Estoque máximo deve ser maior que o mínimo"""
        if v is not None and 'estoque_minimo' in info.data:
            if v < info.data['estoque_minimo']:
                raise ValueError('Estoque máximo deve ser maior ou igual ao mínimo')
        return v


class ProdutoCreate(ProdutoBase):
    """Schema para criação de produto"""
    pass


class ProdutoUpdate(BaseModel):
    """Schema para atualização de produto (campos opcionais)"""
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao: Optional[str] = None
    categoria_id: Optional[int] = None
    unidade_medida: Optional[str] = Field(None, max_length=20)
    estoque_minimo: Optional[Decimal] = Field(None, ge=0)
    estoque_maximo: Optional[Decimal] = Field(None, ge=0)
    preco_referencia: Optional[Decimal] = Field(None, ge=0)
    especificacoes: Optional[Dict[str, Any]] = None
    imagem_url: Optional[str] = Field(None, max_length=500)
    ativo: Optional[bool] = None
    observacoes: Optional[str] = None


class ProdutoResponse(ProdutoBase):
    """Schema para resposta da API"""
    id: int
    tenant_id: int
    estoque_atual: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProdutoListResponse(BaseModel):
    """Schema para listagem paginada"""
    total: int
    items: list[ProdutoResponse]


class ProdutoEstoqueUpdate(BaseModel):
    """Schema para atualização apenas do estoque"""
    estoque_atual: Decimal = Field(..., ge=0, description="Novo valor do estoque")
