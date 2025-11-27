"""
Rotas de Categorias - Refatorado com DRY abstractions
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db, get_current_tenant_id
from app.models.categoria import Categoria
from app.schemas.categoria import (
    CategoriaCreate,
    CategoriaUpdate,
    CategoriaResponse,
    CategoriaListResponse
)
from app.api.utils import get_by_id, validate_fk, paginate_query, apply_search_filter, update_entity

router = APIRouter()


@router.post("/", response_model=CategoriaResponse, status_code=201)
def criar_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Criar nova categoria"""
    # Valida categoria pai se informada
    if categoria.categoria_pai_id:
        validate_fk(db, Categoria, categoria.categoria_pai_id, tenant_id, "Categoria pai")

    db_categoria = Categoria(**categoria.model_dump(), tenant_id=tenant_id)
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria


@router.get("/", response_model=CategoriaListResponse)
def listar_categorias(
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    busca: Optional[str] = Query(None, description="Buscar por nome ou código"),
    categoria_pai_id: Optional[int] = Query(None, description="Filtrar por categoria pai"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Listar categorias com paginação e filtros"""
    query = db.query(Categoria).filter(Categoria.tenant_id == tenant_id)

    # Filtros
    if busca:
        query = apply_search_filter(query, busca, Categoria.nome, Categoria.codigo)
    if categoria_pai_id is not None:
        query = query.filter(Categoria.categoria_pai_id == categoria_pai_id)

    # Paginação
    items, total = paginate_query(query, page, page_size, Categoria.nome)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{categoria_id}", response_model=CategoriaResponse)
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter detalhes de uma categoria específica"""
    return get_by_id(db, Categoria, categoria_id, tenant_id, error_message="Categoria não encontrada")


@router.put("/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    categoria_update: CategoriaUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Atualizar categoria existente"""
    categoria = get_by_id(db, Categoria, categoria_id, tenant_id, error_message="Categoria não encontrada")

    # Validações de categoria pai
    if categoria_update.categoria_pai_id is not None:
        if categoria_update.categoria_pai_id == categoria_id:
            raise HTTPException(status_code=400, detail="Categoria não pode ser pai de si mesma")
        validate_fk(db, Categoria, categoria_update.categoria_pai_id, tenant_id, "Categoria pai")

    return update_entity(db, categoria, categoria_update.model_dump(exclude_unset=True))


@router.delete("/{categoria_id}", status_code=204)
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Deletar categoria (não permite se tiver subcategorias)"""
    categoria = get_by_id(db, Categoria, categoria_id, tenant_id, error_message="Categoria não encontrada")

    # Verifica subcategorias
    tem_subcategorias = db.query(Categoria).filter(
        Categoria.categoria_pai_id == categoria_id,
        Categoria.tenant_id == tenant_id
    ).first()
    if tem_subcategorias:
        raise HTTPException(status_code=400, detail="Não é possível deletar categoria que possui subcategorias")

    db.delete(categoria)
    db.commit()
    return None
