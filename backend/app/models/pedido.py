from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class StatusPedido(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    APROVADO = "APROVADO"
    ENVIADO_FORNECEDOR = "ENVIADO_FORNECEDOR"
    CONFIRMADO = "CONFIRMADO"
    EM_TRANSITO = "EM_TRANSITO"
    ENTREGUE_PARCIAL = "ENTREGUE_PARCIAL"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


class PedidoCompra(Base):
    """
    Pedido de Compra - gerado a partir de uma cotacao vencedora ou manualmente

    Fluxo:
    RASCUNHO -> AGUARDANDO_APROVACAO -> APROVADO -> ENVIADO_FORNECEDOR
    -> CONFIRMADO -> EM_TRANSITO -> ENTREGUE_PARCIAL/ENTREGUE

    Pode ser CANCELADO em qualquer etapa antes de ENTREGUE
    """
    __tablename__ = "pedidos_compra"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # Identificacao
    numero = Column(String(50), nullable=False, index=True)  # PC-AAAA-NNNNN

    # Origem (opcional - pode vir de cotacao)
    solicitacao_cotacao_id = Column(Integer, ForeignKey("solicitacoes_cotacao.id"), nullable=True)
    proposta_id = Column(Integer, ForeignKey("propostas_fornecedor.id"), nullable=True)

    # Fornecedor
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=False)

    # Status e datas
    status = Column(SQLEnum(StatusPedido), default=StatusPedido.RASCUNHO, nullable=False)
    data_pedido = Column(DateTime, server_default=func.now(), nullable=False)
    data_aprovacao = Column(DateTime, nullable=True)
    data_envio = Column(DateTime, nullable=True)
    data_confirmacao = Column(DateTime, nullable=True)
    data_previsao_entrega = Column(DateTime, nullable=True)
    data_entrega = Column(DateTime, nullable=True)

    # Valores
    valor_produtos = Column(Numeric(15, 2), default=0)
    valor_frete = Column(Numeric(15, 2), default=0)
    valor_desconto = Column(Numeric(15, 2), default=0)
    valor_total = Column(Numeric(15, 2), default=0)

    # Condicoes comerciais
    condicoes_pagamento = Column(String(200), nullable=True)
    prazo_entrega = Column(Integer, nullable=True)  # Em dias
    frete_tipo = Column(String(10), nullable=True)  # CIF, FOB

    # Informacoes adicionais
    observacoes = Column(Text, nullable=True)
    observacoes_internas = Column(Text, nullable=True)

    # Aprovacao
    aprovado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    justificativa_aprovacao = Column(Text, nullable=True)

    # Cancelamento
    cancelado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_cancelamento = Column(Text, nullable=True)
    data_cancelamento = Column(DateTime, nullable=True)

    # Auditoria
    created_by = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", backref="pedidos_compra")
    fornecedor = relationship("Fornecedor", backref="pedidos_compra")
    solicitacao_cotacao = relationship("SolicitacaoCotacao", backref="pedidos_gerados")
    proposta = relationship("PropostaFornecedor", backref="pedidos_gerados")
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    criado_por = relationship("Usuario", foreign_keys=[created_by])
    usuario_aprovacao = relationship("Usuario", foreign_keys=[aprovado_por])
    usuario_cancelamento = relationship("Usuario", foreign_keys=[cancelado_por])


class ItemPedido(Base):
    """
    Item do Pedido de Compra
    """
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    pedido_id = Column(Integer, ForeignKey("pedidos_compra.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    # Origem (se veio de cotacao)
    item_proposta_id = Column(Integer, ForeignKey("itens_proposta.id"), nullable=True)

    # Quantidades
    quantidade = Column(Numeric(15, 4), nullable=False)
    quantidade_recebida = Column(Numeric(15, 4), default=0)
    unidade_medida = Column(String(20), default="UN")

    # Valores
    preco_unitario = Column(Numeric(15, 4), nullable=False)
    desconto_percentual = Column(Numeric(5, 2), default=0)
    valor_total = Column(Numeric(15, 2), default=0)

    # Informacoes adicionais
    especificacoes = Column(Text, nullable=True)
    marca = Column(String(100), nullable=True)
    prazo_entrega_item = Column(Integer, nullable=True)  # Em dias

    # Auditoria
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant")
    pedido = relationship("PedidoCompra", back_populates="itens")
    produto = relationship("Produto")
    item_proposta = relationship("ItemProposta")
