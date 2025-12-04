from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import re


class ContatoFornecedor(BaseModel):
    """Schema para contato de fornecedor"""
    nome: str = Field(..., min_length=1, max_length=100)
    cargo: Optional[str] = Field(None, max_length=50)
    telefone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None


class FornecedorBase(BaseModel):
    """Schema base para Fornecedor"""
    razao_social: str = Field(..., min_length=1, max_length=200, description="Razão social")
    nome_fantasia: Optional[str] = Field(None, max_length=200, description="Nome fantasia")
    cnpj: str = Field(..., min_length=14, max_length=14, description="CNPJ (apenas números)")
    inscricao_estadual: Optional[str] = Field(None, max_length=20)

    # Endereço
    endereco_logradouro: Optional[str] = Field(None, max_length=200)
    endereco_numero: Optional[str] = Field(None, max_length=20)
    endereco_complemento: Optional[str] = Field(None, max_length=100)
    endereco_bairro: Optional[str] = Field(None, max_length=100)
    endereco_cidade: Optional[str] = Field(None, max_length=100)
    endereco_estado: Optional[str] = Field(None, min_length=2, max_length=2, description="UF")
    endereco_cep: Optional[str] = Field(None, min_length=8, max_length=8, description="CEP (apenas números)")

    # Contatos
    contatos: Optional[List[ContatoFornecedor]] = Field(None, description="Lista de contatos")
    telefone_principal: Optional[str] = Field(None, max_length=20)
    email_principal: Optional[EmailStr] = None
    whatsapp: Optional[str] = Field(None, max_length=20, description="WhatsApp com DDD (apenas números)")
    website: Optional[str] = Field(None, max_length=200)

    # Condições comerciais
    prazo_entrega_medio: Optional[int] = Field(None, ge=0, description="Prazo médio em dias")
    condicoes_pagamento: Optional[str] = Field(None, description="Ex: 30/60 dias, À vista")
    valor_minimo_pedido: Optional[Decimal] = Field(None, ge=0)
    frete_tipo: Optional[str] = Field(None, max_length=20, description="CIF ou FOB")

    # Status
    ativo: bool = Field(True)
    aprovado: bool = Field(False, description="Fornecedor aprovado para compras")

    # Outros
    observacoes: Optional[str] = None
    categorias_produtos: Optional[List[str]] = Field(None, description="Categorias que fornece")

    @field_validator('cnpj')
    @classmethod
    def validar_cnpj(cls, v):
        """CNPJ deve conter apenas números"""
        if not re.match(r'^\d{14}$', v):
            raise ValueError('CNPJ deve conter exatamente 14 dígitos numéricos')
        return v

    @field_validator('endereco_cep')
    @classmethod
    def validar_cep(cls, v):
        """CEP deve conter apenas números"""
        if v and not re.match(r'^\d{8}$', v):
            raise ValueError('CEP deve conter exatamente 8 dígitos numéricos')
        return v

    @field_validator('endereco_estado')
    @classmethod
    def validar_uf(cls, v):
        """UF deve ser maiúscula"""
        if v:
            return v.upper()
        return v


class FornecedorCreate(FornecedorBase):
    """Schema para criação de fornecedor"""
    categorias_ids: Optional[List[int]] = Field(None, description="IDs das categorias que o fornecedor atende")


class FornecedorUpdate(BaseModel):
    """Schema para atualização de fornecedor (campos opcionais)"""
    razao_social: Optional[str] = Field(None, min_length=1, max_length=200)
    nome_fantasia: Optional[str] = Field(None, max_length=200)
    cnpj: Optional[str] = Field(None, min_length=14, max_length=14)
    inscricao_estadual: Optional[str] = Field(None, max_length=20)
    endereco_logradouro: Optional[str] = Field(None, max_length=200)
    endereco_numero: Optional[str] = Field(None, max_length=20)
    endereco_complemento: Optional[str] = Field(None, max_length=100)
    endereco_bairro: Optional[str] = Field(None, max_length=100)
    endereco_cidade: Optional[str] = Field(None, max_length=100)
    endereco_estado: Optional[str] = Field(None, min_length=2, max_length=2)
    endereco_cep: Optional[str] = Field(None, min_length=8, max_length=8)
    contatos: Optional[List[ContatoFornecedor]] = None
    telefone_principal: Optional[str] = Field(None, max_length=20)
    email_principal: Optional[EmailStr] = None
    whatsapp: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=200)
    prazo_entrega_medio: Optional[int] = Field(None, ge=0)
    condicoes_pagamento: Optional[str] = None
    valor_minimo_pedido: Optional[Decimal] = Field(None, ge=0)
    frete_tipo: Optional[str] = Field(None, max_length=20)
    ativo: Optional[bool] = None
    aprovado: Optional[bool] = None
    observacoes: Optional[str] = None
    categorias_produtos: Optional[List[str]] = None
    categorias_ids: Optional[List[int]] = Field(None, description="IDs das categorias que o fornecedor atende")


class CategoriaSimples(BaseModel):
    """Schema simplificado de categoria para resposta"""
    id: int
    nome: str

    class Config:
        from_attributes = True


class FornecedorResponse(FornecedorBase):
    """Schema para resposta da API"""
    id: int
    tenant_id: int
    rating: Decimal
    total_compras: int
    valor_total_comprado: Decimal
    created_at: datetime
    updated_at: datetime
    categorias: Optional[List[CategoriaSimples]] = Field(None, description="Categorias que o fornecedor atende")

    class Config:
        from_attributes = True


class FornecedorListResponse(BaseModel):
    """Schema para listagem paginada"""
    total: int
    items: list[FornecedorResponse]


class FornecedorAvaliacaoUpdate(BaseModel):
    """Schema para atualização da avaliação"""
    rating: Decimal = Field(..., ge=0, le=5, description="Avaliação de 0 a 5")
