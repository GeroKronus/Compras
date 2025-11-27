"""
Rotas de Fornecedores - Refatorado com DRY abstractions
Inclui endpoints de ranking por tempo de resposta
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from app.api.deps import get_db, get_current_tenant_id
from app.models.fornecedor import Fornecedor
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


@router.post("/", response_model=FornecedorResponse, status_code=201)
def criar_fornecedor(
    fornecedor: FornecedorCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Criar novo fornecedor"""
    validate_unique(db, Fornecedor, "cnpj", fornecedor.cnpj, tenant_id, display_name="CNPJ")

    db_fornecedor = Fornecedor(**fornecedor.model_dump(), tenant_id=tenant_id)
    db.add(db_fornecedor)
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

    return update_entity(db, fornecedor, fornecedor_update.model_dump(exclude_unset=True))


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
