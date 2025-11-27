"""
Status Helpers - Validação de status de entidades
"""
from typing import TypeVar, Union, List
from enum import Enum
from fastapi import HTTPException

T = TypeVar('T')


def require_status(
    entity: T,
    required: Union[Enum, List[Enum]],
    operation: str = None
) -> None:
    """
    Valida que entidade está em um dos status requeridos.

    Args:
        entity: Entidade com campo 'status'
        required: Status requerido ou lista de status permitidos
        operation: Nome da operação para mensagem de erro

    Raises:
        HTTPException 400 se status não for permitido

    Usage:
        require_status(pedido, StatusPedido.RASCUNHO, "edição")
        require_status(pedido, [StatusPedido.APROVADO, StatusPedido.RASCUNHO], "envio")
    """
    allowed = required if isinstance(required, list) else [required]

    if entity.status not in allowed:
        allowed_str = ", ".join(s.value for s in allowed)
        msg = f"Operação não permitida no status {entity.status.value}"
        if operation:
            msg = f"{operation} não permitida no status {entity.status.value}"
        msg += f". Status permitido(s): {allowed_str}"
        raise HTTPException(status_code=400, detail=msg)


def forbid_status(
    entity: T,
    forbidden: Union[Enum, List[Enum]],
    operation: str = None
) -> None:
    """
    Valida que entidade NÃO está em status proibido.

    Args:
        entity: Entidade com campo 'status'
        forbidden: Status proibido ou lista de status proibidos
        operation: Nome da operação para mensagem de erro

    Raises:
        HTTPException 400 se status for proibido

    Usage:
        forbid_status(pedido, StatusPedido.CANCELADO, "edição")
        forbid_status(solicitacao, [StatusSolicitacao.CANCELADA, StatusSolicitacao.FINALIZADA])
    """
    blocked = forbidden if isinstance(forbidden, list) else [forbidden]

    if entity.status in blocked:
        blocked_str = ", ".join(s.value for s in blocked)
        msg = f"Operação não permitida no status {entity.status.value}"
        if operation:
            msg = f"{operation} não permitida no status {entity.status.value}"
        raise HTTPException(status_code=400, detail=msg)


def transition_status(
    entity: T,
    new_status: Enum,
    allowed_transitions: dict = None
) -> T:
    """
    Transiciona status com validação de transições permitidas.

    Args:
        entity: Entidade com campo 'status'
        new_status: Novo status
        allowed_transitions: Dict de {status_atual: [status_permitidos]}

    Returns:
        Entidade com status atualizado

    Raises:
        HTTPException 400 se transição não for permitida

    Usage:
        TRANSITIONS = {
            StatusPedido.RASCUNHO: [StatusPedido.AGUARDANDO_APROVACAO, StatusPedido.CANCELADO],
            StatusPedido.AGUARDANDO_APROVACAO: [StatusPedido.APROVADO, StatusPedido.CANCELADO],
        }
        pedido = transition_status(pedido, StatusPedido.APROVADO, TRANSITIONS)
    """
    if allowed_transitions:
        current = entity.status
        allowed = allowed_transitions.get(current, [])

        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Transição de {current.value} para {new_status.value} não permitida"
            )

    entity.status = new_status
    return entity
