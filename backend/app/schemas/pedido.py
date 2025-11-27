from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class StatusPedido(str, Enum):
    RASCUNHO = "RASCUNHO"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    APROVADO = "APROVADO"
    ENVIADO_FORNECEDOR = "ENVIADO_FORNECEDOR"
    CONFIRMADO = "CONFIRMADO"
    EM_TRANSITO = "EM_TRANSITO"
    ENTREGUE_PARCIAL = "ENTREGUE_PARCIAL"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


# ============ ITEM PEDIDO ============

class ItemPedidoBase(BaseModel):
    produto_id: int
    quantidade: Decimal = Field(..., gt=0)
    unidade_medida: str = Field(default="UN", max_length=20)
    preco_unitario: Decimal = Field(..., gt=0)
    desconto_percentual: Decimal = Field(default=0, ge=0, le=100)
    especificacoes: Optional[str] = None
    marca: Optional[str] = Field(None, max_length=100)
    prazo_entrega_item: Optional[int] = Field(None, ge=1)


class ItemPedidoCreate(ItemPedidoBase):
    item_proposta_id: Optional[int] = None


class ItemPedidoUpdate(BaseModel):
    quantidade: Optional[Decimal] = Field(None, gt=0)
    preco_unitario: Optional[Decimal] = Field(None, gt=0)
    desconto_percentual: Optional[Decimal] = Field(None, ge=0, le=100)
    especificacoes: Optional[str] = None
    marca: Optional[str] = Field(None, max_length=100)
    prazo_entrega_item: Optional[int] = Field(None, ge=1)


class ItemPedidoResponse(ItemPedidoBase):
    id: int
    pedido_id: int
    item_proposta_id: Optional[int] = None
    quantidade_recebida: Decimal = 0
    valor_total: Decimal = 0
    tenant_id: int
    created_at: datetime
    produto_nome: Optional[str] = None
    produto_codigo: Optional[str] = None

    class Config:
        from_attributes = True


# ============ PEDIDO COMPRA ============

class PedidoCompraBase(BaseModel):
    fornecedor_id: int
    condicoes_pagamento: Optional[str] = Field(None, max_length=200)
    prazo_entrega: Optional[int] = Field(None, ge=1)
    frete_tipo: Optional[str] = Field(None, max_length=10)
    valor_frete: Decimal = Field(default=0, ge=0)
    observacoes: Optional[str] = None
    observacoes_internas: Optional[str] = None
    data_previsao_entrega: Optional[datetime] = None


class PedidoCompraCreate(PedidoCompraBase):
    solicitacao_cotacao_id: Optional[int] = None
    proposta_id: Optional[int] = None
    itens: List[ItemPedidoCreate] = Field(default_factory=list)


class PedidoCompraCreateFromCotacao(BaseModel):
    """Schema para gerar pedido a partir de uma cotacao vencedora"""
    proposta_id: int
    observacoes: Optional[str] = None
    observacoes_internas: Optional[str] = None


class PedidoCompraUpdate(BaseModel):
    condicoes_pagamento: Optional[str] = Field(None, max_length=200)
    prazo_entrega: Optional[int] = Field(None, ge=1)
    frete_tipo: Optional[str] = Field(None, max_length=10)
    valor_frete: Optional[Decimal] = Field(None, ge=0)
    observacoes: Optional[str] = None
    observacoes_internas: Optional[str] = None
    data_previsao_entrega: Optional[datetime] = None


class PedidoCompraResponse(PedidoCompraBase):
    id: int
    numero: str
    solicitacao_cotacao_id: Optional[int] = None
    proposta_id: Optional[int] = None
    status: StatusPedido
    data_pedido: datetime
    data_aprovacao: Optional[datetime] = None
    data_envio: Optional[datetime] = None
    data_confirmacao: Optional[datetime] = None
    data_entrega: Optional[datetime] = None
    valor_produtos: Decimal = 0
    valor_desconto: Decimal = 0
    valor_total: Decimal = 0
    aprovado_por: Optional[int] = None
    justificativa_aprovacao: Optional[str] = None
    cancelado_por: Optional[int] = None
    motivo_cancelamento: Optional[str] = None
    data_cancelamento: Optional[datetime] = None
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    itens: List[ItemPedidoResponse] = []
    fornecedor_nome: Optional[str] = None
    fornecedor_cnpj: Optional[str] = None
    solicitacao_numero: Optional[str] = None

    class Config:
        from_attributes = True


class PedidoCompraListResponse(BaseModel):
    items: List[PedidoCompraResponse]
    total: int
    page: int
    page_size: int


# ============ ACOES ESPECIAIS ============

class EnviarPedidoRequest(BaseModel):
    """Enviar pedido para fornecedor"""
    pass  # Nenhum campo necessario, apenas confirma o envio


class AprovarPedidoRequest(BaseModel):
    """Aprovar pedido"""
    justificativa: str = Field(..., min_length=5)


class CancelarPedidoRequest(BaseModel):
    """Cancelar pedido"""
    motivo: str = Field(..., min_length=10)


class ConfirmarRecebimentoRequest(BaseModel):
    """Confirmar recebimento (parcial ou total)"""
    itens: List[dict]  # [{item_id: int, quantidade_recebida: Decimal}]
    observacoes: Optional[str] = None


# ============ RESUMOS ============

class ResumoPedidosResponse(BaseModel):
    total_pedidos: int
    valor_total: Decimal
    pedidos_por_status: dict
    pedidos_por_fornecedor: List[dict]
