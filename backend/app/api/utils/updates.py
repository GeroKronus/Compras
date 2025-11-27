"""
Update Helpers - Funções para atualização de entidades
"""
from typing import TypeVar, List
from sqlalchemy.orm import Session
from pydantic import BaseModel

T = TypeVar('T')


def update_entity(
    db: Session,
    entity: T,
    update_data: BaseModel,
    exclude_fields: List[str] = None,
    commit: bool = True
) -> T:
    """
    Atualiza entidade com dados do schema Pydantic.

    Args:
        db: Sessão do banco
        entity: Entidade a atualizar
        update_data: Schema Pydantic com dados de atualização
        exclude_fields: Campos a ignorar na atualização
        commit: Se deve fazer commit automático

    Returns:
        Entidade atualizada

    Usage:
        produto = update_entity(db, produto, produto_update)
        pedido = update_entity(db, pedido, pedido_update, exclude_fields=["status"])
    """
    data = update_data.model_dump(exclude_unset=True)

    if exclude_fields:
        data = {k: v for k, v in data.items() if k not in exclude_fields}

    for field, value in data.items():
        if hasattr(entity, field):
            setattr(entity, field, value)

    if commit:
        db.commit()
        db.refresh(entity)

    return entity


def bulk_update(
    db: Session,
    entities: List[T],
    field_updates: dict,
    commit: bool = True
) -> List[T]:
    """
    Atualiza múltiplas entidades com os mesmos valores.

    Args:
        db: Sessão do banco
        entities: Lista de entidades
        field_updates: Dict de {campo: valor}
        commit: Se deve fazer commit

    Returns:
        Lista de entidades atualizadas

    Usage:
        items = bulk_update(db, pedido.itens, {"status": "ENTREGUE"})
    """
    for entity in entities:
        for field, value in field_updates.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

    if commit:
        db.commit()
        for entity in entities:
            db.refresh(entity)

    return entities
