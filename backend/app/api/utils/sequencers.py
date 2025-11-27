"""
Sequencers - Geradores de números sequenciais
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Type, TypeVar

T = TypeVar('T')


def generate_sequential_number(
    db: Session,
    model: Type[T],
    prefix: str,
    tenant_id: int,
    year: int = None,
    digits: int = 5
) -> str:
    """
    Gera número sequencial no formato: PREFIX-AAAA-NNNNN

    Args:
        db: Sessão do banco
        model: Modelo que possui campo 'numero'
        prefix: Prefixo (ex: "SC", "PC", "NF")
        tenant_id: ID do tenant
        year: Ano (default: ano atual)
        digits: Quantidade de dígitos para padding (default: 5)

    Returns:
        Número formatado (ex: "PC-2025-00001")

    Usage:
        numero = generate_sequential_number(db, PedidoCompra, "PC", tenant_id)
        # Retorna: "PC-2025-00001"

        numero = generate_sequential_number(db, SolicitacaoCotacao, "SC", tenant_id)
        # Retorna: "SC-2025-00001"
    """
    ano = year or datetime.now().year
    pattern = f"{prefix}-{ano}-%"

    ultimo = db.query(func.max(model.numero)).filter(
        model.tenant_id == tenant_id,
        model.numero.like(pattern)
    ).scalar()

    if ultimo:
        # Extrai o número sequencial do formato PREFIX-AAAA-NNNNN
        seq = int(ultimo.split("-")[-1]) + 1
    else:
        seq = 1

    return f"{prefix}-{ano}-{seq:0{digits}d}"


# Constantes de prefixos para padronização
class Prefixes:
    SOLICITACAO_COTACAO = "SC"
    PEDIDO_COMPRA = "PC"
    NOTA_FISCAL = "NF"
    RECEBIMENTO = "RC"
    ORDEM_SERVICO = "OS"
