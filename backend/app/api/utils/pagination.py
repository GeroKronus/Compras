"""
Pagination Helpers - Funções utilitárias para paginação e filtros
"""
from typing import TypeVar, Any, Optional, Tuple, List
from sqlalchemy.orm import Query
from sqlalchemy import or_

T = TypeVar('T')


def paginate_query(
    query: Query,
    page: int = 1,
    page_size: int = 20,
    order_by: Any = None
) -> Tuple[List[T], int]:
    """
    Aplica paginação em uma query e retorna itens + total.

    Args:
        query: Query SQLAlchemy
        page: Número da página (1-indexed)
        page_size: Tamanho da página
        order_by: Coluna(s) para ordenação - pode ser único ou tupla

    Returns:
        Tupla (lista_de_itens, total)

    Usage:
        items, total = paginate_query(query, page=1, page_size=20, order_by=Produto.nome)
        items, total = paginate_query(query, page=1, page_size=20, order_by=(desc(Produto.rating), Produto.nome))
    """
    total = query.count()

    if order_by is not None:
        if isinstance(order_by, tuple):
            query = query.order_by(*order_by)
        else:
            query = query.order_by(order_by)

    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return items, total


def paginate_response(
    query: Query,
    page: int = 1,
    page_size: int = 20,
    order_by: Any = None,
    transform_fn: callable = None
) -> dict:
    """
    Aplica paginação e retorna dict pronto para response.

    Args:
        query: Query SQLAlchemy
        page: Número da página
        page_size: Tamanho da página
        order_by: Coluna(s) para ordenação
        transform_fn: Função para transformar cada item (opcional)

    Returns:
        Dict com items, total, page, page_size

    Usage:
        return paginate_response(query, page, page_size, Produto.created_at.desc())
    """
    items, total = paginate_query(query, page, page_size, order_by)

    if transform_fn:
        items = [transform_fn(item) for item in items]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


def apply_search_filter(
    query: Query,
    search_term: Optional[str],
    *fields
) -> Query:
    """
    Aplica filtro de busca ILIKE em múltiplos campos.

    Args:
        query: Query SQLAlchemy
        search_term: Termo de busca
        *fields: Campos para buscar (ex: Model.nome, Model.codigo)

    Returns:
        Query com filtro aplicado

    Usage:
        query = apply_search_filter(query, busca, Produto.nome, Produto.codigo, Produto.descricao)
    """
    if not search_term or not fields:
        return query

    conditions = [field.ilike(f"%{search_term}%") for field in fields]
    return query.filter(or_(*conditions))


def apply_filters(
    query: Query,
    filters: dict[str, tuple]
) -> Query:
    """
    Aplica múltiplos filtros de uma vez.

    Args:
        query: Query SQLAlchemy
        filters: Dict de {valor: (campo, operador)}
                 operador pode ser: "eq", "like", "in", "gt", "lt", "gte", "lte"

    Returns:
        Query com filtros aplicados

    Usage:
        query = apply_filters(query, {
            status: (Pedido.status, "eq"),
            fornecedor_id: (Pedido.fornecedor_id, "eq"),
        })
    """
    for value, (field, operator) in filters.items():
        if value is None:
            continue

        if operator == "eq":
            query = query.filter(field == value)
        elif operator == "like":
            query = query.filter(field.ilike(f"%{value}%"))
        elif operator == "in":
            query = query.filter(field.in_(value))
        elif operator == "gt":
            query = query.filter(field > value)
        elif operator == "lt":
            query = query.filter(field < value)
        elif operator == "gte":
            query = query.filter(field >= value)
        elif operator == "lte":
            query = query.filter(field <= value)

    return query
