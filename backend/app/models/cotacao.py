from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, DateTime, Date, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from app.models.base import Base, TenantMixin, TimestampMixin, AuditMixin
from datetime import datetime
import enum


class StatusSolicitacao(str, enum.Enum):
    """Status da solicitacao de cotacao"""
    RASCUNHO = "RASCUNHO"
    ENVIADA = "ENVIADA"
    EM_COTACAO = "EM_COTACAO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class StatusProposta(str, enum.Enum):
    """Status da proposta do fornecedor"""
    PENDENTE = "PENDENTE"
    RECEBIDA = "RECEBIDA"
    APROVADA = "APROVADA"
    REJEITADA = "REJEITADA"
    VENCEDORA = "VENCEDORA"


class SolicitacaoCotacao(Base, TenantMixin, TimestampMixin, AuditMixin):
    """
    Solicitacao de Cotacao enviada aos fornecedores

    Fluxo:
    1. Comprador cria solicitacao (RASCUNHO)
    2. Adiciona itens e fornecedores
    3. Envia para fornecedores (ENVIADA)
    4. Fornecedores enviam propostas (EM_COTACAO)
    5. Comprador escolhe vencedor (FINALIZADA)
    """
    __tablename__ = "solicitacoes_cotacao"

    id = Column(Integer, primary_key=True, index=True)

    # Identificacao
    numero = Column(String(20), nullable=False)  # SC-2024-00001
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)

    # Status
    status = Column(
        Enum(StatusSolicitacao, name='status_solicitacao_enum', create_type=False),
        default=StatusSolicitacao.RASCUNHO,
        nullable=False
    )

    # Datas
    data_abertura = Column(DateTime, default=datetime.utcnow)
    data_limite_proposta = Column(DateTime, nullable=True)
    data_fechamento = Column(DateTime, nullable=True)

    # Prioridade e urgencia
    urgente = Column(Boolean, default=False)
    motivo_urgencia = Column(Text, nullable=True)

    # Observacoes
    observacoes = Column(Text, nullable=True)
    condicoes_pagamento_desejadas = Column(String(200), nullable=True)
    prazo_entrega_desejado = Column(Integer, nullable=True)  # dias

    # Resultado
    proposta_vencedora_id = Column(Integer, ForeignKey('propostas_fornecedor.id'), nullable=True)
    justificativa_escolha = Column(Text, nullable=True)

    # Relacionamentos
    itens = relationship("ItemSolicitacao", back_populates="solicitacao", cascade="all, delete-orphan")
    propostas = relationship("PropostaFornecedor", back_populates="solicitacao", foreign_keys="PropostaFornecedor.solicitacao_id")

    def __repr__(self):
        return f"<SolicitacaoCotacao {self.numero} - {self.status}>"

    __table_args__ = (
        Index('idx_solic_tenant_id', 'tenant_id', 'id'),
        Index('idx_solic_tenant_numero', 'tenant_id', 'numero'),
        Index('idx_solic_tenant_status', 'tenant_id', 'status'),
    )


class ItemSolicitacao(Base, TenantMixin, TimestampMixin):
    """
    Item dentro de uma Solicitacao de Cotacao
    """
    __tablename__ = "itens_solicitacao"

    id = Column(Integer, primary_key=True, index=True)

    solicitacao_id = Column(Integer, ForeignKey('solicitacoes_cotacao.id'), nullable=False)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)

    # Quantidade
    quantidade = Column(Numeric(10, 2), nullable=False)
    unidade_medida = Column(String(20), default="UN")

    # Especificacoes adicionais
    especificacoes = Column(Text, nullable=True)

    # Relacionamentos
    solicitacao = relationship("SolicitacaoCotacao", back_populates="itens")
    produto = relationship("Produto")
    itens_proposta = relationship("ItemProposta", back_populates="item_solicitacao")

    __table_args__ = (
        Index('idx_item_solic_tenant', 'tenant_id', 'solicitacao_id'),
    )


class PropostaFornecedor(Base, TenantMixin, TimestampMixin, AuditMixin):
    """
    Proposta enviada por um fornecedor para uma Solicitacao
    """
    __tablename__ = "propostas_fornecedor"

    id = Column(Integer, primary_key=True, index=True)

    solicitacao_id = Column(Integer, ForeignKey('solicitacoes_cotacao.id'), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey('fornecedores.id'), nullable=False)

    # Status
    status = Column(
        Enum(StatusProposta, name='status_proposta_enum', create_type=False),
        default=StatusProposta.PENDENTE,
        nullable=False
    )

    # Datas
    data_envio_solicitacao = Column(DateTime, nullable=True)
    data_recebimento = Column(DateTime, nullable=True)

    # Condicoes comerciais
    condicoes_pagamento = Column(String(200), nullable=True)
    prazo_entrega = Column(Integer, nullable=True)  # dias
    validade_proposta = Column(Date, nullable=True)

    # Valores totais
    valor_total = Column(Numeric(12, 2), nullable=True)
    desconto_total = Column(Numeric(5, 2), default=0)  # percentual

    # Frete
    frete_tipo = Column(String(10), nullable=True)  # CIF, FOB
    frete_valor = Column(Numeric(10, 2), nullable=True)

    # Observacoes
    observacoes = Column(Text, nullable=True)

    # Avaliacao (preenchido apos escolha)
    score_preco = Column(Numeric(3, 2), nullable=True)  # 0-5
    score_prazo = Column(Numeric(3, 2), nullable=True)
    score_condicoes = Column(Numeric(3, 2), nullable=True)
    score_total = Column(Numeric(3, 2), nullable=True)

    # Relacionamentos
    solicitacao = relationship("SolicitacaoCotacao", back_populates="propostas", foreign_keys=[solicitacao_id])
    fornecedor = relationship("Fornecedor")
    itens = relationship("ItemProposta", back_populates="proposta", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PropostaFornecedor {self.id} - Fornecedor {self.fornecedor_id}>"

    __table_args__ = (
        Index('idx_proposta_tenant_solic', 'tenant_id', 'solicitacao_id'),
        Index('idx_proposta_tenant_forn', 'tenant_id', 'fornecedor_id'),
        Index('idx_proposta_tenant_status', 'tenant_id', 'status'),
    )


class ItemProposta(Base, TenantMixin, TimestampMixin):
    """
    Item cotado dentro de uma Proposta
    """
    __tablename__ = "itens_proposta"

    id = Column(Integer, primary_key=True, index=True)

    proposta_id = Column(Integer, ForeignKey('propostas_fornecedor.id'), nullable=False)
    item_solicitacao_id = Column(Integer, ForeignKey('itens_solicitacao.id'), nullable=False)

    # Preco
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    quantidade_disponivel = Column(Numeric(10, 2), nullable=True)  # Pode ser diferente do solicitado

    # Desconto
    desconto_percentual = Column(Numeric(5, 2), default=0)
    preco_final = Column(Numeric(10, 2), nullable=True)  # Calculado

    # Prazo especifico do item
    prazo_entrega_item = Column(Integer, nullable=True)  # dias

    # Observacoes
    observacoes = Column(Text, nullable=True)
    marca_oferecida = Column(String(100), nullable=True)

    # Relacionamentos
    proposta = relationship("PropostaFornecedor", back_populates="itens")
    item_solicitacao = relationship("ItemSolicitacao", back_populates="itens_proposta")

    __table_args__ = (
        Index('idx_item_prop_tenant', 'tenant_id', 'proposta_id'),
    )
