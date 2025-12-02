from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class StatusSolicitacao(str, Enum):
    RASCUNHO = "RASCUNHO"
    ENVIADA = "ENVIADA"
    EM_COTACAO = "EM_COTACAO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class StatusProposta(str, Enum):
    PENDENTE = "PENDENTE"
    RECEBIDA = "RECEBIDA"
    APROVADA = "APROVADA"
    REJEITADA = "REJEITADA"
    VENCEDORA = "VENCEDORA"


# ============ ITEM SOLICITACAO ============

class ItemSolicitacaoBase(BaseModel):
    produto_id: int
    quantidade: Decimal = Field(..., gt=0)
    unidade_medida: str = Field(default="UN", max_length=20)
    especificacoes: Optional[str] = None


class ItemSolicitacaoCreate(ItemSolicitacaoBase):
    pass


class ItemSolicitacaoUpdate(BaseModel):
    quantidade: Optional[Decimal] = Field(None, gt=0)
    unidade_medida: Optional[str] = Field(None, max_length=20)
    especificacoes: Optional[str] = None


class ItemSolicitacaoResponse(ItemSolicitacaoBase):
    id: int
    solicitacao_id: int
    tenant_id: int
    created_at: datetime
    produto_nome: Optional[str] = None
    produto_codigo: Optional[str] = None

    class Config:
        from_attributes = True


# ============ SOLICITACAO COTACAO ============

class SolicitacaoCotacaoBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descricao: Optional[str] = None
    data_limite_proposta: Optional[datetime] = None
    urgente: bool = False
    motivo_urgencia: Optional[str] = None
    observacoes: Optional[str] = None
    condicoes_pagamento_desejadas: Optional[str] = Field(None, max_length=200)
    prazo_entrega_desejado: Optional[int] = Field(None, ge=1)


class SolicitacaoCotacaoCreate(SolicitacaoCotacaoBase):
    itens: List[ItemSolicitacaoCreate] = Field(default_factory=list)
    fornecedores_ids: List[int] = Field(default_factory=list)

    @field_validator('itens')
    @classmethod
    def validar_itens(cls, v):
        if len(v) == 0:
            raise ValueError('Solicitacao deve ter pelo menos um item')
        return v


class SolicitacaoCotacaoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=200)
    descricao: Optional[str] = None
    data_limite_proposta: Optional[datetime] = None
    urgente: Optional[bool] = None
    motivo_urgencia: Optional[str] = None
    observacoes: Optional[str] = None
    condicoes_pagamento_desejadas: Optional[str] = Field(None, max_length=200)
    prazo_entrega_desejado: Optional[int] = Field(None, ge=1)


class SolicitacaoCotacaoResponse(SolicitacaoCotacaoBase):
    id: int
    numero: str
    status: StatusSolicitacao
    data_abertura: datetime
    data_fechamento: Optional[datetime] = None
    proposta_vencedora_id: Optional[int] = None
    justificativa_escolha: Optional[str] = None
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    itens: List[ItemSolicitacaoResponse] = []
    total_propostas: Optional[int] = None

    class Config:
        from_attributes = True


class SolicitacaoCotacaoListResponse(BaseModel):
    items: List[SolicitacaoCotacaoResponse]
    total: int
    page: int
    page_size: int


# ============ ITEM PROPOSTA ============

class ItemPropostaBase(BaseModel):
    item_solicitacao_id: int
    preco_unitario: Decimal = Field(..., gt=0)
    quantidade_disponivel: Optional[Decimal] = Field(None, gt=0)
    desconto_percentual: Decimal = Field(default=0, ge=0, le=100)
    prazo_entrega_item: Optional[int] = Field(None, ge=1)
    observacoes: Optional[str] = None
    marca_oferecida: Optional[str] = Field(None, max_length=100)


class ItemPropostaCreate(ItemPropostaBase):
    pass


class ItemPropostaUpdate(BaseModel):
    preco_unitario: Optional[Decimal] = Field(None, gt=0)
    quantidade_disponivel: Optional[Decimal] = Field(None, gt=0)
    desconto_percentual: Optional[Decimal] = Field(None, ge=0, le=100)
    prazo_entrega_item: Optional[int] = Field(None, ge=1)
    observacoes: Optional[str] = None
    marca_oferecida: Optional[str] = Field(None, max_length=100)


class ItemPropostaResponse(ItemPropostaBase):
    id: int
    proposta_id: int
    preco_final: Optional[Decimal] = None
    tenant_id: int
    created_at: datetime
    produto_nome: Optional[str] = None
    quantidade_solicitada: Optional[Decimal] = None

    class Config:
        from_attributes = True


# ============ PROPOSTA FORNECEDOR ============

class PropostaFornecedorBase(BaseModel):
    condicoes_pagamento: Optional[str] = Field(None, max_length=200)
    prazo_entrega: Optional[int] = Field(None, ge=1)
    validade_proposta: Optional[date] = None
    frete_tipo: Optional[str] = Field(None, max_length=10)
    frete_valor: Optional[Decimal] = Field(None, ge=0)
    observacoes: Optional[str] = None


class PropostaFornecedorCreate(PropostaFornecedorBase):
    solicitacao_id: int
    fornecedor_id: int
    itens: List[ItemPropostaCreate] = Field(default_factory=list)


class PropostaFornecedorUpdate(PropostaFornecedorBase):
    valor_total: Optional[Decimal] = Field(None, ge=0)
    desconto_total: Optional[Decimal] = Field(None, ge=0, le=100)


class PropostaFornecedorResponse(PropostaFornecedorBase):
    id: int
    solicitacao_id: int
    fornecedor_id: int
    status: StatusProposta
    data_envio_solicitacao: Optional[datetime] = None
    data_recebimento: Optional[datetime] = None
    valor_total: Optional[Decimal] = None
    desconto_total: Decimal = 0
    score_preco: Optional[Decimal] = None
    score_prazo: Optional[Decimal] = None
    score_condicoes: Optional[Decimal] = None
    score_total: Optional[Decimal] = None
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    itens: List[ItemPropostaResponse] = []
    fornecedor_nome: Optional[str] = None
    fornecedor_cnpj: Optional[str] = None

    class Config:
        from_attributes = True


class PropostaFornecedorListResponse(BaseModel):
    items: List[PropostaFornecedorResponse]
    total: int


# ============ ACOES ESPECIAIS ============

class EnviarSolicitacaoRequest(BaseModel):
    fornecedores_ids: List[int] = Field(..., min_length=1)


class RegistrarPropostaRequest(PropostaFornecedorBase):
    itens: List[ItemPropostaCreate] = Field(..., min_length=1)


class EscolherVencedorRequest(BaseModel):
    proposta_id: int
    justificativa: str = Field(..., min_length=10)


# ============ MAPA COMPARATIVO ============

class ItemMapaComparativo(BaseModel):
    item_solicitacao_id: int
    produto_id: int
    produto_nome: str
    produto_codigo: str
    quantidade_solicitada: Decimal
    propostas: List[dict]  # Lista de propostas com precos


class MapaComparativoResponse(BaseModel):
    solicitacao_id: int
    solicitacao_numero: str
    solicitacao_titulo: str
    itens: List[ItemMapaComparativo]
    resumo: dict  # Totais por fornecedor


# ============ SUGESTAO IA ============

class SugestaoIAResponse(BaseModel):
    proposta_sugerida_id: int
    fornecedor_nome: str
    score_total: Decimal
    motivos: List[str]
    economia_estimada: Optional[Decimal] = None
    alertas: List[str] = []


# ============ ANÁLISE OTIMIZADA POR ITEM ============

class PrecoFornecedorItem(BaseModel):
    """Preço de um fornecedor para um item específico"""
    fornecedor_id: int
    fornecedor_nome: str
    proposta_id: int
    item_proposta_id: int
    preco_unitario: Decimal
    desconto_percentual: Decimal = Decimal(0)
    preco_final: Decimal  # unitário com desconto
    preco_total: Decimal  # preco_final * quantidade
    prazo_entrega: Optional[int] = None
    condicoes_pagamento: Optional[str] = None
    marca_oferecida: Optional[str] = None
    is_menor_preco: bool = False
    diferenca_percentual: Optional[Decimal] = None  # vs menor preço


class AnaliseItemResponse(BaseModel):
    """Análise de um item com preços de todos os fornecedores"""
    item_solicitacao_id: int
    produto_id: int
    produto_nome: str
    produto_codigo: Optional[str] = None
    quantidade: Decimal
    unidade_medida: str
    precos_fornecedores: List[PrecoFornecedorItem]
    menor_preco_unitario: Optional[Decimal] = None
    menor_preco_total: Optional[Decimal] = None
    fornecedor_menor_preco_id: Optional[int] = None
    fornecedor_menor_preco_nome: Optional[str] = None


class ResumoFornecedor(BaseModel):
    """Resumo de valores por fornecedor"""
    fornecedor_id: int
    fornecedor_nome: str
    proposta_id: int
    valor_total: Decimal
    prazo_entrega: Optional[int] = None
    condicoes_pagamento: Optional[str] = None
    qtd_itens_cotados: int
    qtd_itens_menor_preco: int  # quantos itens este fornecedor tem o menor preço


class ItemOtimizado(BaseModel):
    """Item com fornecedor otimizado selecionado"""
    item_solicitacao_id: int
    produto_id: int
    produto_nome: str
    quantidade: Decimal
    fornecedor_id: int
    fornecedor_nome: str
    proposta_id: int
    item_proposta_id: int
    preco_unitario: Decimal
    preco_total: Decimal


class CompraOtimizadaPorFornecedor(BaseModel):
    """Agrupamento de itens por fornecedor para OC"""
    fornecedor_id: int
    fornecedor_nome: str
    proposta_id: int
    itens: List[ItemOtimizado]
    valor_total: Decimal
    prazo_entrega: Optional[int] = None
    condicoes_pagamento: Optional[str] = None


class AnaliseOtimizadaResponse(BaseModel):
    """Resposta completa da análise otimizada"""
    solicitacao_id: int
    solicitacao_numero: str
    solicitacao_titulo: str

    # Análise por item
    itens: List[AnaliseItemResponse]

    # Resumo por fornecedor (compra única)
    resumo_fornecedores: List[ResumoFornecedor]

    # Comparativo
    menor_valor_global: Decimal  # menor valor comprando tudo de 1 fornecedor
    fornecedor_menor_global_id: int
    fornecedor_menor_global_nome: str

    # Compra otimizada (split)
    valor_otimizado: Decimal  # valor comprando melhor de cada fornecedor
    economia_otimizada: Decimal  # diferença entre menor global e otimizado
    economia_percentual: Decimal
    compra_otimizada: List[CompraOtimizadaPorFornecedor]

    # Recomendação
    recomendacao: str  # "COMPRA_UNICA" ou "COMPRA_OTIMIZADA"
    justificativa: str


class GerarOCsOtimizadasRequest(BaseModel):
    """Request para gerar múltiplas OCs otimizadas"""
    solicitacao_id: int
    # Lista de seleções: qual fornecedor para cada item
    selecoes: List[dict]  # [{item_solicitacao_id, fornecedor_id, item_proposta_id}]
    justificativa: str = Field(..., min_length=10)


class OCGerada(BaseModel):
    """OC gerada no processo otimizado"""
    pedido_id: int
    pedido_numero: str
    fornecedor_id: int
    fornecedor_nome: str
    valor_total: Decimal
    qtd_itens: int


class GerarOCsOtimizadasResponse(BaseModel):
    """Resposta da geração de múltiplas OCs"""
    solicitacao_id: int
    ocs_geradas: List[OCGerada]
    valor_total: Decimal
    economia_vs_menor_global: Optional[Decimal] = None
