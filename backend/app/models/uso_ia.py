"""
Model para rastreamento de uso da IA
Controle de creditos e limites por tenant
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class TipoOperacaoIA(enum.Enum):
    ANALISE_PROPOSTA = "analise_proposta"       # Analise de melhor proposta
    EXTRACAO_EMAIL = "extracao_email"           # Extracai de dados de email
    CLASSIFICACAO_EMAIL = "classificacao_email"  # Classificacao automatica de email
    OUTRO = "outro"


class UsoIA(Base):
    """
    Registro de cada chamada a API da IA.
    Permite controlar creditos e limites por tenant.
    """
    __tablename__ = "uso_ia"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Tipo de operacao
    tipo_operacao = Column(String(50), nullable=False)

    # Dados da chamada
    modelo = Column(String(50), nullable=False)  # claude-sonnet-4-20250514, etc
    tokens_entrada = Column(Integer, nullable=False, default=0)
    tokens_saida = Column(Integer, nullable=False, default=0)
    tokens_total = Column(Integer, nullable=False, default=0)

    # Custo estimado (em USD)
    custo_estimado = Column(Numeric(10, 6), nullable=False, default=0)

    # Contexto da operacao
    referencia_id = Column(Integer, nullable=True)  # ID da solicitacao, email, etc
    referencia_tipo = Column(String(50), nullable=True)  # solicitacao, email, etc
    descricao = Column(Text, nullable=True)

    # Usuario que disparou a operacao
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", backref="uso_ia")
    usuario = relationship("Usuario", backref="uso_ia")


class LimiteIATenant(Base):
    """
    Limites de uso da IA por tenant.
    Define quanto cada tenant pode usar por mes.
    """
    __tablename__ = "limites_ia_tenant"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Limites mensais
    tokens_mensais_limite = Column(Integer, nullable=False, default=100000)  # 100k tokens/mes
    chamadas_mensais_limite = Column(Integer, nullable=False, default=500)   # 500 chamadas/mes
    custo_mensal_limite = Column(Numeric(10, 2), nullable=False, default=10.00)  # $10/mes

    # Uso atual (resetado mensalmente)
    tokens_usados_mes = Column(Integer, nullable=False, default=0)
    chamadas_usadas_mes = Column(Integer, nullable=False, default=0)
    custo_usado_mes = Column(Numeric(10, 2), nullable=False, default=0)

    # Mes de referencia
    mes_referencia = Column(String(7), nullable=False)  # "2025-11"

    # Chave propria do tenant (opcional)
    chave_api_propria = Column(String(255), nullable=True)
    usar_chave_propria = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    tenant = relationship("Tenant", backref="limite_ia")
