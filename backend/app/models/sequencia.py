"""
Modelo para controle de sequências numéricas
Garante que números nunca reiniciem mesmo se registros forem deletados
"""
from sqlalchemy import Column, Integer, String, UniqueConstraint
from app.models.base import Base


class Sequencia(Base):
    """
    Armazena o último número usado para cada tipo de sequência por tenant/ano.
    Esta tabela NUNCA deve ser limpa, garantindo sequência contínua.
    """
    __tablename__ = "sequencias"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    prefixo = Column(String(10), nullable=False)  # SC, PC, NF, etc
    ano = Column(Integer, nullable=False)
    ultimo_numero = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'prefixo', 'ano', name='uq_sequencia_tenant_prefixo_ano'),
    )
