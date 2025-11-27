"""
Model para rastreamento de emails processados
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class StatusEmailProcessado(str, enum.Enum):
    """Enum que herda de str para garantir serialização correta para PostgreSQL"""
    PENDENTE = "pendente"           # Aguardando classificacao
    CLASSIFICADO = "classificado"   # Associado a uma solicitacao
    IGNORADO = "ignorado"           # Marcado para ignorar
    ERRO = "erro"                   # Erro no processamento


class MetodoClassificacao(str, enum.Enum):
    """Enum que herda de str para garantir serialização correta para PostgreSQL"""
    ASSUNTO = "assunto"             # Classificado pelo assunto (COTACAO #XXX)
    REMETENTE = "remetente"         # Classificado pelo email do fornecedor
    IA = "ia"                       # Classificado pela IA
    MANUAL = "manual"               # Classificado manualmente pelo usuario


# Criar tipos PostgreSQL ENUM
status_email_enum = PG_ENUM(
    'pendente', 'classificado', 'ignorado', 'erro',
    name='statusemailprocessado',
    create_type=True
)

metodo_classificacao_enum = PG_ENUM(
    'assunto', 'remetente', 'ia', 'manual',
    name='metodoclassificacao',
    create_type=True
)


class EmailProcessado(Base):
    __tablename__ = "emails_processados"

    id = Column(Integer, primary_key=True, index=True)

    # Identificacao unica do email no servidor IMAP
    email_uid = Column(String(100), nullable=False, index=True)
    message_id = Column(String(255), nullable=True)  # Message-ID header

    # Dados do email
    remetente = Column(String(255), nullable=False)
    remetente_nome = Column(String(255), nullable=True)
    assunto = Column(String(500), nullable=False)
    data_recebimento = Column(DateTime, nullable=False)
    corpo_resumo = Column(Text, nullable=True)  # Primeiros 1000 chars
    corpo_completo = Column(Text, nullable=True)  # Corpo inteiro para analise

    # Classificacao - usando tipos PostgreSQL diretamente
    status = Column(status_email_enum, default='pendente')
    metodo_classificacao = Column(metodo_classificacao_enum, nullable=True)
    confianca_ia = Column(Integer, nullable=True)  # 0-100
    motivo_classificacao = Column(Text, nullable=True)  # Explicacao da IA

    # Associacoes
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes_cotacao.id", ondelete="SET NULL"), nullable=True)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id", ondelete="SET NULL"), nullable=True)
    proposta_id = Column(Integer, ForeignKey("propostas_fornecedor.id", ondelete="SET NULL"), nullable=True)

    # Dados extraidos pela IA
    dados_extraidos = Column(Text, nullable=True)  # JSON com dados da proposta

    # Multi-tenant
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Timestamps
    processado_em = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    solicitacao = relationship("SolicitacaoCotacao", backref="emails_processados")
    fornecedor = relationship("Fornecedor", backref="emails_recebidos")
    proposta = relationship("PropostaFornecedor", backref="email_origem")
