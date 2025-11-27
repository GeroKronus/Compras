"""
Model para auditoria de escolhas de fornecedor
Registra quando o comprador escolhe uma opcao diferente da recomendada
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base, TenantMixin, TimestampMixin
from datetime import datetime


class AuditoriaEscolhaFornecedor(Base, TenantMixin, TimestampMixin):
    """
    Registro de auditoria quando a escolha diverge da recomendacao do sistema

    Campos:
    - solicitacao: A cotacao em questao
    - proposta_escolhida: O fornecedor que foi escolhido
    - proposta_recomendada: O fornecedor recomendado (menor preco)
    - valor_escolhido: Valor da proposta escolhida
    - valor_recomendado: Valor da proposta recomendada
    - diferenca_valor: Quanto a mais foi pago
    - justificativa: Motivo dado pelo comprador
    - usuario: Quem fez a escolha
    - revisado_admin: Se o admin ja revisou
    """
    __tablename__ = "auditoria_escolha_fornecedor"

    id = Column(Integer, primary_key=True, index=True)

    # Referencia a solicitacao
    solicitacao_id = Column(Integer, ForeignKey('solicitacoes_cotacao.id'), nullable=False)
    solicitacao_numero = Column(String(20), nullable=False)  # Cache para facil consulta

    # Proposta escolhida (diferente da recomendada)
    proposta_escolhida_id = Column(Integer, ForeignKey('propostas_fornecedor.id'), nullable=False)
    fornecedor_escolhido_nome = Column(String(200), nullable=False)
    valor_escolhido = Column(Numeric(12, 2), nullable=False)

    # Proposta recomendada (menor preco)
    proposta_recomendada_id = Column(Integer, ForeignKey('propostas_fornecedor.id'), nullable=False)
    fornecedor_recomendado_nome = Column(String(200), nullable=False)
    valor_recomendado = Column(Numeric(12, 2), nullable=False)

    # Diferenca
    diferenca_valor = Column(Numeric(12, 2), nullable=False)  # Quanto a mais foi pago
    diferenca_percentual = Column(Numeric(5, 2), nullable=False)  # % a mais

    # Justificativa do comprador
    justificativa = Column(Text, nullable=False)

    # Usuario que fez a escolha
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    usuario_nome = Column(String(100), nullable=True)

    # Data da escolha
    data_escolha = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Revisao pelo admin
    revisado_admin = Column(Boolean, default=False)
    data_revisao = Column(DateTime, nullable=True)
    observacao_admin = Column(Text, nullable=True)

    # Relacionamentos
    solicitacao = relationship("SolicitacaoCotacao", foreign_keys=[solicitacao_id])
    proposta_escolhida = relationship("PropostaFornecedor", foreign_keys=[proposta_escolhida_id])
    proposta_recomendada = relationship("PropostaFornecedor", foreign_keys=[proposta_recomendada_id])

    __table_args__ = (
        Index('idx_auditoria_tenant', 'tenant_id'),
        Index('idx_auditoria_tenant_revisado', 'tenant_id', 'revisado_admin'),
        Index('idx_auditoria_data', 'data_escolha'),
    )

    def __repr__(self):
        return f"<AuditoriaEscolha SC={self.solicitacao_numero} Diff={self.diferenca_valor}>"
