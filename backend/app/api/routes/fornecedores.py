"""
Rotas de Fornecedores - Refatorado com DRY abstractions
Inclui endpoints de ranking por tempo de resposta
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Optional, List
from app.api.deps import get_db, get_current_tenant_id
from app.models.fornecedor import Fornecedor
from app.models.categoria import Categoria
from app.models.categoria_fornecedor import categoria_fornecedor
from app.schemas.fornecedor import (
    FornecedorCreate,
    FornecedorUpdate,
    FornecedorResponse,
    FornecedorListResponse,
    FornecedorAvaliacaoUpdate
)
from app.api.utils import (
    get_by_id, validate_unique,
    paginate_query, apply_search_filter, update_entity
)
from app.services.fornecedor_ranking_service import fornecedor_ranking_service

router = APIRouter()


def _sincronizar_categorias(db: Session, fornecedor_id: int, categorias_ids: List[int], tenant_id: int):
    """Sincroniza as categorias do fornecedor (remove antigas e adiciona novas)"""
    # Remover categorias existentes
    db.execute(
        categoria_fornecedor.delete().where(
            categoria_fornecedor.c.fornecedor_id == fornecedor_id,
            categoria_fornecedor.c.tenant_id == tenant_id
        )
    )

    # Adicionar novas categorias
    if categorias_ids:
        for cat_id in categorias_ids:
            # Verificar se categoria existe e pertence ao tenant
            categoria = db.query(Categoria).filter(
                Categoria.id == cat_id,
                Categoria.tenant_id == tenant_id
            ).first()
            if categoria:
                db.execute(
                    categoria_fornecedor.insert().values(
                        categoria_id=cat_id,
                        fornecedor_id=fornecedor_id,
                        tenant_id=tenant_id
                    )
                )


@router.post("/", response_model=FornecedorResponse, status_code=201)
def criar_fornecedor(
    fornecedor: FornecedorCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Criar novo fornecedor"""
    validate_unique(db, Fornecedor, "cnpj", fornecedor.cnpj, tenant_id, display_name="CNPJ")

    # Separar categorias_ids dos dados do fornecedor
    fornecedor_data = fornecedor.model_dump(exclude={"categorias_ids"})
    categorias_ids = fornecedor.categorias_ids

    db_fornecedor = Fornecedor(**fornecedor_data, tenant_id=tenant_id)
    db.add(db_fornecedor)
    db.flush()  # Para obter o ID

    # Sincronizar categorias
    if categorias_ids:
        _sincronizar_categorias(db, db_fornecedor.id, categorias_ids, tenant_id)

    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor


@router.get("/", response_model=FornecedorListResponse)
def listar_fornecedores(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    busca: Optional[str] = Query(None, description="Buscar por razão social, nome fantasia ou CNPJ"),
    ativo: Optional[bool] = Query(None),
    aprovado: Optional[bool] = Query(None),
    categoria_produto: Optional[str] = Query(None, description="Filtrar por categoria de produto"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Listar fornecedores com paginação e filtros"""
    query = db.query(Fornecedor).filter(Fornecedor.tenant_id == tenant_id)

    # Filtros
    if busca:
        query = apply_search_filter(query, busca, Fornecedor.razao_social, Fornecedor.nome_fantasia, Fornecedor.cnpj)
    if ativo is not None:
        query = query.filter(Fornecedor.ativo == ativo)
    if aprovado is not None:
        query = query.filter(Fornecedor.aprovado == aprovado)
    if categoria_produto:
        query = query.filter(Fornecedor.categorias_produtos.contains([categoria_produto]))

    # Ordenar por rating (melhores primeiro)
    items, total = paginate_query(query, page, page_size, (desc(Fornecedor.rating), Fornecedor.razao_social))
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{fornecedor_id}", response_model=FornecedorResponse)
def obter_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter detalhes de um fornecedor específico"""
    return get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")


@router.put("/{fornecedor_id}", response_model=FornecedorResponse)
def atualizar_fornecedor(
    fornecedor_id: int,
    fornecedor_update: FornecedorUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Atualizar fornecedor existente"""
    fornecedor = get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")

    # Verifica CNPJ duplicado
    if fornecedor_update.cnpj and fornecedor_update.cnpj != fornecedor.cnpj:
        validate_unique(db, Fornecedor, "cnpj", fornecedor_update.cnpj, tenant_id, exclude_id=fornecedor_id, display_name="CNPJ")

    # Separar categorias_ids dos dados de atualização
    update_data = fornecedor_update.model_dump(exclude_unset=True)
    categorias_ids = update_data.pop("categorias_ids", None)

    # Atualizar categorias se fornecidas
    if categorias_ids is not None:
        _sincronizar_categorias(db, fornecedor_id, categorias_ids, tenant_id)

    return update_entity(db, fornecedor, update_data)


@router.patch("/{fornecedor_id}/avaliacao", response_model=FornecedorResponse)
def atualizar_avaliacao(
    fornecedor_id: int,
    avaliacao: FornecedorAvaliacaoUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Atualizar avaliação (rating) do fornecedor"""
    fornecedor = get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")
    return update_entity(db, fornecedor, {"rating": avaliacao.rating})


@router.patch("/{fornecedor_id}/aprovar", response_model=FornecedorResponse)
def aprovar_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Aprovar fornecedor para realizar compras"""
    fornecedor = get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")
    return update_entity(db, fornecedor, {"aprovado": True})


@router.patch("/{fornecedor_id}/reprovar", response_model=FornecedorResponse)
def reprovar_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Reprovar fornecedor"""
    fornecedor = get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")
    return update_entity(db, fornecedor, {"aprovado": False})


@router.delete("/{fornecedor_id}", status_code=204)
def deletar_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Deletar fornecedor"""
    fornecedor = get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")
    db.delete(fornecedor)
    db.commit()
    return None


# ============ ENDPOINTS DE RANKING ============

@router.get("/ranking/tempo-resposta")
def obter_ranking_fornecedores(
    limite: int = Query(10, ge=1, le=50, description="Quantidade de fornecedores a retornar"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Obter ranking dos melhores fornecedores por tempo de resposta.

    Retorna lista ordenada por rating (baseado em tempo de resposta e performance).

    O rating considera:
    - Tempo de resposta as cotacoes (40% do peso)
    - Historico de qualidade/preco (60% do peso)

    Classificacao de tempo:
    - Excelente: < 4 horas
    - Muito bom: 4-12 horas
    - Bom: 12-24 horas
    - Regular: 24-48 horas
    - Lento: > 48 horas
    """
    return fornecedor_ranking_service.obter_ranking_fornecedores(
        db=db,
        tenant_id=tenant_id,
        limite=limite
    )


@router.get("/{fornecedor_id}/estatisticas")
def obter_estatisticas_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Obter estatisticas detalhadas de um fornecedor especifico.

    Retorna:
    - Rating geral
    - Total de cotacoes solicitadas/respondidas
    - Taxa de sucesso (cotacoes vencidas)
    - Tempo medio/minimo/maximo de resposta
    - Historico de compras
    """
    # Verifica se fornecedor pertence ao tenant
    get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")

    return fornecedor_ranking_service.obter_estatisticas_fornecedor(
        db=db,
        fornecedor_id=fornecedor_id
    )


# ============ ENDPOINTS DE CATEGORIAS ============

@router.get("/por-categoria/{categoria_id}")
def listar_fornecedores_por_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Listar fornecedores que atendem uma categoria específica.

    Útil para sugestão de fornecedores na criação de solicitação de cotação.
    """
    # Buscar fornecedores vinculados à categoria
    fornecedores = db.query(Fornecedor).join(
        categoria_fornecedor,
        Fornecedor.id == categoria_fornecedor.c.fornecedor_id
    ).filter(
        categoria_fornecedor.c.categoria_id == categoria_id,
        categoria_fornecedor.c.tenant_id == tenant_id,
        Fornecedor.tenant_id == tenant_id,
        Fornecedor.ativo == True
    ).options(joinedload(Fornecedor.categorias)).all()

    return {
        "categoria_id": categoria_id,
        "total": len(fornecedores),
        "fornecedores": [
            {
                "id": f.id,
                "razao_social": f.razao_social,
                "nome_fantasia": f.nome_fantasia,
                "cnpj": f.cnpj,
                "email_principal": f.email_principal,
                "telefone_principal": f.telefone_principal,
                "rating": float(f.rating) if f.rating else 0,
                "aprovado": f.aprovado,
                "categorias": [{"id": c.id, "nome": c.nome} for c in f.categorias]
            }
            for f in fornecedores
        ]
    }


@router.get("/por-categorias")
def listar_fornecedores_por_categorias(
    categorias_ids: str = Query(..., description="IDs das categorias separados por vírgula. Ex: 1,2,3"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Listar fornecedores que atendem uma ou mais categorias.

    Usado para sugestão de fornecedores baseado nos produtos de uma SC.
    Retorna fornecedores únicos que atendem pelo menos uma das categorias.
    """
    # Converter string para lista de IDs
    try:
        ids = [int(x.strip()) for x in categorias_ids.split(",") if x.strip()]
    except ValueError:
        return {"error": "IDs de categorias inválidos", "fornecedores": []}

    if not ids:
        return {"categorias_ids": [], "total": 0, "fornecedores": []}

    # Buscar fornecedores que atendem pelo menos uma das categorias
    fornecedores = db.query(Fornecedor).join(
        categoria_fornecedor,
        Fornecedor.id == categoria_fornecedor.c.fornecedor_id
    ).filter(
        categoria_fornecedor.c.categoria_id.in_(ids),
        categoria_fornecedor.c.tenant_id == tenant_id,
        Fornecedor.tenant_id == tenant_id,
        Fornecedor.ativo == True
    ).options(joinedload(Fornecedor.categorias)).distinct().all()

    return {
        "categorias_ids": ids,
        "total": len(fornecedores),
        "fornecedores": [
            {
                "id": f.id,
                "razao_social": f.razao_social,
                "nome_fantasia": f.nome_fantasia,
                "cnpj": f.cnpj,
                "email_principal": f.email_principal,
                "telefone_principal": f.telefone_principal,
                "rating": float(f.rating) if f.rating else 0,
                "aprovado": f.aprovado,
                "categorias": [{"id": c.id, "nome": c.nome} for c in f.categorias]
            }
            for f in fornecedores
        ]
    }


@router.put("/{fornecedor_id}/categorias")
def atualizar_categorias_fornecedor(
    fornecedor_id: int,
    categorias_ids: List[int],
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Atualizar categorias de um fornecedor.

    Substitui todas as categorias existentes pelas novas.
    """
    fornecedor = get_by_id(db, Fornecedor, fornecedor_id, tenant_id, error_message="Fornecedor não encontrado")

    _sincronizar_categorias(db, fornecedor_id, categorias_ids, tenant_id)
    db.commit()
    db.refresh(fornecedor)

    return {
        "fornecedor_id": fornecedor_id,
        "razao_social": fornecedor.razao_social,
        "categorias": [{"id": c.id, "nome": c.nome} for c in fornecedor.categorias]
    }
