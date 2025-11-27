"""
Models do sistema - Multi-tenant

IMPORTANTE: Todos os models herdam de TenantMixin, que adiciona tenant_id
Isso garante isolamento de dados entre empresas
"""

from app.models.base import Base, TenantMixin, TimestampMixin, AuditMixin
from app.models.tenant import Tenant
from app.models.usuario import Usuario, TipoUsuario
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.fornecedor import Fornecedor
from app.models.cotacao import (
    SolicitacaoCotacao,
    ItemSolicitacao,
    PropostaFornecedor,
    ItemProposta,
    StatusSolicitacao,
    StatusProposta,
)
from app.models.pedido import (
    PedidoCompra,
    ItemPedido,
    StatusPedido,
)
from app.models.email_processado import (
    EmailProcessado,
    StatusEmailProcessado,
    MetodoClassificacao,
)
from app.models.auditoria_escolha import AuditoriaEscolhaFornecedor

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "AuditMixin",
    "Tenant",
    "Usuario",
    "TipoUsuario",
    "Categoria",
    "Produto",
    "Fornecedor",
    "SolicitacaoCotacao",
    "ItemSolicitacao",
    "PropostaFornecedor",
    "ItemProposta",
    "StatusSolicitacao",
    "StatusProposta",
    "PedidoCompra",
    "ItemPedido",
    "StatusPedido",
    "AuditoriaEscolhaFornecedor",
]
