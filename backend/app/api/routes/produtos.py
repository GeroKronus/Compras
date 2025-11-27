"""
Rotas de Produtos - Refatorado com DRY abstractions
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.api.deps import get_db, get_current_tenant_id
from app.models.produto import Produto
from app.models.categoria import Categoria
from app.models.fornecedor import Fornecedor
from app.models.produto_fornecedor import produto_fornecedor
from app.schemas.produto import (
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoResponse,
    ProdutoListResponse,
    ProdutoEstoqueUpdate
)
from app.api.utils import (
    get_by_id, validate_fk, validate_unique,
    paginate_query, apply_search_filter, update_entity
)

router = APIRouter()


@router.post("/", response_model=ProdutoResponse, status_code=201)
def criar_produto(
    produto: ProdutoCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Criar novo produto"""
    # Validações
    validate_unique(db, Produto, "codigo", produto.codigo, tenant_id, display_name="Código de produto")
    if produto.categoria_id:
        validate_fk(db, Categoria, produto.categoria_id, tenant_id, "Categoria")

    db_produto = Produto(**produto.model_dump(), tenant_id=tenant_id)
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto


@router.get("/", response_model=ProdutoListResponse)
def listar_produtos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    busca: Optional[str] = Query(None, description="Buscar por código, nome ou descrição"),
    categoria_id: Optional[int] = Query(None),
    ativo: Optional[bool] = Query(None),
    estoque_baixo: bool = Query(False, description="Apenas produtos com estoque abaixo do mínimo"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Listar produtos com paginação e filtros"""
    query = db.query(Produto).filter(Produto.tenant_id == tenant_id)

    # Filtros
    if busca:
        query = apply_search_filter(query, busca, Produto.codigo, Produto.nome, Produto.descricao)
    if categoria_id is not None:
        query = query.filter(Produto.categoria_id == categoria_id)
    if ativo is not None:
        query = query.filter(Produto.ativo == ativo)
    if estoque_baixo:
        query = query.filter(Produto.estoque_atual < Produto.estoque_minimo)

    items, total = paginate_query(query, page, page_size, Produto.nome)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{produto_id}", response_model=ProdutoResponse)
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter detalhes de um produto específico"""
    return get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")


@router.put("/{produto_id}", response_model=ProdutoResponse)
def atualizar_produto(
    produto_id: int,
    produto_update: ProdutoUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Atualizar produto existente"""
    produto = get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")

    # Validações
    if produto_update.codigo and produto_update.codigo != produto.codigo:
        validate_unique(db, Produto, "codigo", produto_update.codigo, tenant_id, exclude_id=produto_id, display_name="Código de produto")
    if produto_update.categoria_id is not None:
        validate_fk(db, Categoria, produto_update.categoria_id, tenant_id, "Categoria")

    return update_entity(db, produto, produto_update.model_dump(exclude_unset=True))


@router.patch("/{produto_id}/estoque", response_model=ProdutoResponse)
def atualizar_estoque(
    produto_id: int,
    estoque_update: ProdutoEstoqueUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Atualizar apenas o estoque do produto"""
    produto = get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")
    return update_entity(db, produto, {"estoque_atual": estoque_update.estoque_atual})


@router.delete("/{produto_id}", status_code=204)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Deletar produto"""
    produto = get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")
    db.delete(produto)
    db.commit()
    return None


# ============ FORNECEDORES DO PRODUTO ============

@router.get("/{produto_id}/fornecedores")
def listar_fornecedores_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Listar fornecedores associados a um produto"""
    produto = get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")

    fornecedores = db.query(Fornecedor).join(
        produto_fornecedor,
        Fornecedor.id == produto_fornecedor.c.fornecedor_id
    ).filter(
        produto_fornecedor.c.produto_id == produto_id,
        produto_fornecedor.c.tenant_id == tenant_id
    ).all()

    return {
        "produto_id": produto_id,
        "produto_nome": produto.nome,
        "fornecedores": [
            {
                "id": f.id,
                "razao_social": f.razao_social,
                "nome_fantasia": f.nome_fantasia,
                "cnpj": f.cnpj,
                "email": f.email_principal,
                "telefone": f.telefone_principal
            }
            for f in fornecedores
        ]
    }


@router.post("/{produto_id}/fornecedores")
def adicionar_fornecedores_produto(
    produto_id: int,
    fornecedores_ids: List[int],
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Adicionar fornecedores a um produto"""
    produto = get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")

    adicionados = []
    ja_existentes = []

    for forn_id in fornecedores_ids:
        # Validar fornecedor
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == forn_id,
            Fornecedor.tenant_id == tenant_id
        ).first()

        if not fornecedor:
            continue

        # Verificar se já existe associação
        existe = db.execute(
            produto_fornecedor.select().where(
                produto_fornecedor.c.produto_id == produto_id,
                produto_fornecedor.c.fornecedor_id == forn_id,
                produto_fornecedor.c.tenant_id == tenant_id
            )
        ).first()

        if existe:
            ja_existentes.append(fornecedor.razao_social)
            continue

        # Criar associação
        db.execute(
            produto_fornecedor.insert().values(
                produto_id=produto_id,
                fornecedor_id=forn_id,
                tenant_id=tenant_id
            )
        )
        adicionados.append(fornecedor.razao_social)

    db.commit()

    return {
        "produto_id": produto_id,
        "adicionados": adicionados,
        "ja_existentes": ja_existentes,
        "mensagem": f"{len(adicionados)} fornecedor(es) adicionado(s)"
    }


@router.delete("/{produto_id}/fornecedores/{fornecedor_id}", status_code=204)
def remover_fornecedor_produto(
    produto_id: int,
    fornecedor_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Remover um fornecedor de um produto"""
    get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")

    db.execute(
        produto_fornecedor.delete().where(
            produto_fornecedor.c.produto_id == produto_id,
            produto_fornecedor.c.fornecedor_id == fornecedor_id,
            produto_fornecedor.c.tenant_id == tenant_id
        )
    )
    db.commit()
    return None


@router.put("/{produto_id}/fornecedores")
def definir_fornecedores_produto(
    produto_id: int,
    fornecedores_ids: List[int],
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Substituir todos os fornecedores de um produto"""
    produto = get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto não encontrado")

    # Remover todos os fornecedores atuais
    db.execute(
        produto_fornecedor.delete().where(
            produto_fornecedor.c.produto_id == produto_id,
            produto_fornecedor.c.tenant_id == tenant_id
        )
    )

    # Adicionar novos
    adicionados = []
    for forn_id in fornecedores_ids:
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == forn_id,
            Fornecedor.tenant_id == tenant_id
        ).first()

        if fornecedor:
            db.execute(
                produto_fornecedor.insert().values(
                    produto_id=produto_id,
                    fornecedor_id=forn_id,
                    tenant_id=tenant_id
                )
            )
            adicionados.append(fornecedor.razao_social)

    db.commit()

    return {
        "produto_id": produto_id,
        "produto_nome": produto.nome,
        "fornecedores": adicionados,
        "total": len(adicionados)
    }
