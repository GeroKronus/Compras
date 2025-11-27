"""
Database Helpers - Funções utilitárias para operações de banco de dados
Elimina duplicação de código em todas as rotas
"""
from typing import Type, TypeVar, Optional, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

T = TypeVar('T')


def get_by_id(
    db: Session,
    model: Type[T],
    entity_id: int,
    tenant_id: int,
    raise_not_found: bool = True,
    error_message: str = None,
    options: list = None
) -> Optional[T]:
    """
    Busca entidade por ID e Tenant ID com validação automática.

    Args:
        db: Sessão do banco de dados
        model: Classe do modelo SQLAlchemy
        entity_id: ID da entidade
        tenant_id: ID do tenant para isolamento multi-tenant
        raise_not_found: Se True, levanta HTTPException 404 quando não encontrado
        error_message: Mensagem customizada de erro (opcional)
        options: Lista de joinedload options (opcional)

    Returns:
        Entidade encontrada ou None

    Raises:
        HTTPException 404 se raise_not_found=True e entidade não existir

    Usage:
        produto = get_by_id(db, Produto, produto_id, tenant_id)
        # ou com options
        pedido = get_by_id(db, Pedido, id, tenant_id, options=[joinedload(Pedido.itens)])
    """
    query = db.query(model).filter(
        model.id == entity_id,
        model.tenant_id == tenant_id
    )

    if options:
        for opt in options:
            query = query.options(opt)

    entity = query.first()

    if not entity and raise_not_found:
        msg = error_message or f"{model.__name__} não encontrado"
        raise HTTPException(status_code=404, detail=msg)

    return entity


def validate_fk(
    db: Session,
    model: Type[T],
    fk_id: int,
    tenant_id: int,
    field_name: str = None
) -> T:
    """
    Valida existência de uma Foreign Key dentro do tenant.

    Args:
        db: Sessão do banco de dados
        model: Classe do modelo da FK
        fk_id: ID da FK a validar
        tenant_id: ID do tenant
        field_name: Nome do campo para mensagem de erro (opcional)

    Returns:
        Entidade da FK se existir

    Raises:
        HTTPException 404 se FK não existir

    Usage:
        fornecedor = validate_fk(db, Fornecedor, fornecedor_id, tenant_id)
        categoria = validate_fk(db, Categoria, categoria_id, tenant_id, "Categoria")
    """
    entity = db.query(model).filter(
        model.id == fk_id,
        model.tenant_id == tenant_id
    ).first()

    if not entity:
        name = field_name or model.__name__
        raise HTTPException(status_code=404, detail=f"{name} não encontrado")

    return entity


def validate_unique(
    db: Session,
    model: Type[T],
    field_name: str,
    field_value: Any,
    tenant_id: int,
    exclude_id: int = None,
    display_name: str = None
) -> None:
    """
    Valida unicidade de campo dentro do tenant.

    Args:
        db: Sessão do banco de dados
        model: Classe do modelo
        field_name: Nome do campo a validar
        field_value: Valor do campo
        tenant_id: ID do tenant
        exclude_id: ID a excluir da validação (para updates)
        display_name: Nome do campo para exibição na mensagem

    Raises:
        HTTPException 400 se valor já existir

    Usage:
        validate_unique(db, Fornecedor, "cnpj", cnpj, tenant_id)
        validate_unique(db, Produto, "codigo", codigo, tenant_id, exclude_id=produto.id)
    """
    field = getattr(model, field_name)
    query = db.query(model).filter(
        field == field_value,
        model.tenant_id == tenant_id
    )

    if exclude_id:
        query = query.filter(model.id != exclude_id)

    if query.first():
        name = display_name or field_name
        raise HTTPException(status_code=400, detail=f"{name} já cadastrado")


def bulk_validate_fks(
    db: Session,
    model: Type[T],
    fk_ids: list[int],
    tenant_id: int,
    field_name: str = None
) -> list[T]:
    """
    Valida múltiplas FKs de uma vez (útil para listas de fornecedores, produtos, etc.)

    Args:
        db: Sessão do banco
        model: Modelo da FK
        fk_ids: Lista de IDs para validar
        tenant_id: ID do tenant
        field_name: Nome do campo para mensagem

    Returns:
        Lista de entidades encontradas

    Raises:
        HTTPException 404 se alguma FK não existir
    """
    if not fk_ids:
        return []

    entities = db.query(model).filter(
        model.id.in_(fk_ids),
        model.tenant_id == tenant_id
    ).all()

    found_ids = {e.id for e in entities}
    missing = set(fk_ids) - found_ids

    if missing:
        name = field_name or model.__name__
        raise HTTPException(
            status_code=404,
            detail=f"{name}(s) não encontrado(s): {list(missing)}"
        )

    return entities
