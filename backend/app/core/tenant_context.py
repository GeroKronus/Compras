from contextvars import ContextVar
from typing import Optional

# Context var para armazenar o tenant_id da requisição atual
# Isso permite que qualquer parte do código acesse o tenant_id sem passar como parâmetro
_tenant_id_ctx_var: ContextVar[Optional[int]] = ContextVar('tenant_id', default=None)


def get_current_tenant_id() -> Optional[int]:
    """
    Obtém o tenant_id do contexto da requisição atual
    """
    return _tenant_id_ctx_var.get()


def set_current_tenant_id(tenant_id: int) -> None:
    """
    Define o tenant_id no contexto da requisição atual
    """
    _tenant_id_ctx_var.set(tenant_id)


def clear_current_tenant_id() -> None:
    """
    Limpa o tenant_id do contexto
    """
    _tenant_id_ctx_var.set(None)
