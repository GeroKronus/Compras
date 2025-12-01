"""
Sequencers - Geradores de números sequenciais

IMPORTANTE: Usa tabela 'sequencias' para garantir que números NUNCA reiniciem,
mesmo se os registros forem deletados. A sequência é persistente e sempre incrementa.
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

    IMPORTANTE: Usa tabela 'sequencias' para garantir persistência.
    Números NUNCA reiniciam, mesmo se registros forem deletados.

    Args:
        db: Sessão do banco
        model: Modelo que possui campo 'numero' (usado apenas para compatibilidade)
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
    from app.models.sequencia import Sequencia

    ano = year or datetime.now().year

    # Buscar ou criar registro de sequência
    sequencia = db.query(Sequencia).filter(
        Sequencia.tenant_id == tenant_id,
        Sequencia.prefixo == prefix,
        Sequencia.ano == ano
    ).first()

    if not sequencia:
        # Primeira vez: verificar se há registros existentes no modelo para migração
        pattern = f"{prefix}-{ano}-%"
        ultimo_existente = db.query(func.max(model.numero)).filter(
            model.tenant_id == tenant_id,
            model.numero.like(pattern)
        ).scalar()

        ultimo_numero = 0
        if ultimo_existente:
            ultimo_numero = int(ultimo_existente.split("-")[-1])

        sequencia = Sequencia(
            tenant_id=tenant_id,
            prefixo=prefix,
            ano=ano,
            ultimo_numero=ultimo_numero
        )
        db.add(sequencia)

    # Incrementar sequência
    sequencia.ultimo_numero += 1
    proximo = sequencia.ultimo_numero

    # Flush para garantir que o número seja reservado
    db.flush()

    return f"{prefix}-{ano}-{proximo:0{digits}d}"


# Constantes de prefixos para padronização
class Prefixes:
    SOLICITACAO_COTACAO = "SC"
    PEDIDO_COMPRA = "PC"
    NOTA_FISCAL = "NF"
    RECEBIMENTO = "RC"
    ORDEM_SERVICO = "OS"
