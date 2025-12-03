from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.api.deps import get_db, get_current_tenant_id, get_current_user
from app.api.utils import get_by_id, validate_fk, paginate_response
from app.models.pedido import PedidoCompra, ItemPedido, StatusPedido
from app.models.cotacao import PropostaFornecedor, ItemProposta, SolicitacaoCotacao, StatusProposta
from app.models.produto import Produto
from app.models.fornecedor import Fornecedor
from app.models.usuario import Usuario
from app.schemas.pedido import (
    PedidoCompraCreate, PedidoCompraUpdate, PedidoCompraResponse,
    PedidoCompraListResponse, PedidoCompraCreateFromCotacao,
    ItemPedidoResponse, AprovarPedidoRequest, CancelarPedidoRequest
)

router = APIRouter()


# ============ FUNCOES AUXILIARES ============

def gerar_numero_pedido(db: Session, tenant_id: int) -> str:
    """Gera numero sequencial para pedido: PC-AAAA-NNNNN"""
    ano = datetime.now().year
    ultimo = db.query(func.max(PedidoCompra.numero)).filter(
        PedidoCompra.tenant_id == tenant_id,
        PedidoCompra.numero.like(f"PC-{ano}-%")
    ).scalar()

    if ultimo:
        seq = int(ultimo.split("-")[-1]) + 1
    else:
        seq = 1

    return f"PC-{ano}-{seq:05d}"


def calcular_totais_pedido(pedido: PedidoCompra):
    """Recalcula os valores totais do pedido"""
    valor_produtos = Decimal(0)
    valor_desconto = Decimal(0)

    for item in pedido.itens:
        subtotal = item.quantidade * item.preco_unitario
        desconto = subtotal * (item.desconto_percentual / 100)
        item.valor_total = subtotal - desconto
        valor_produtos += subtotal
        valor_desconto += desconto

    pedido.valor_produtos = valor_produtos
    pedido.valor_desconto = valor_desconto
    pedido.valor_total = valor_produtos - valor_desconto + (pedido.valor_frete or 0)


def _enrich_pedido_response(pedido: PedidoCompra, db: Session) -> dict:
    """Enriquecer resposta do pedido com dados relacionados"""
    response = {
        "id": pedido.id,
        "numero": pedido.numero,
        "fornecedor_id": pedido.fornecedor_id,
        "solicitacao_cotacao_id": pedido.solicitacao_cotacao_id,
        "proposta_id": pedido.proposta_id,
        "status": pedido.status,
        "data_pedido": pedido.data_pedido,
        "data_aprovacao": pedido.data_aprovacao,
        "data_envio": pedido.data_envio,
        "data_confirmacao": pedido.data_confirmacao,
        "data_previsao_entrega": pedido.data_previsao_entrega,
        "data_entrega": pedido.data_entrega,
        "valor_produtos": pedido.valor_produtos,
        "valor_frete": pedido.valor_frete,
        "valor_desconto": pedido.valor_desconto,
        "valor_total": pedido.valor_total,
        "condicoes_pagamento": pedido.condicoes_pagamento,
        "prazo_entrega": pedido.prazo_entrega,
        "frete_tipo": pedido.frete_tipo,
        "observacoes": pedido.observacoes,
        "observacoes_internas": pedido.observacoes_internas,
        "aprovado_por": pedido.aprovado_por,
        "justificativa_aprovacao": pedido.justificativa_aprovacao,
        "cancelado_por": pedido.cancelado_por,
        "motivo_cancelamento": pedido.motivo_cancelamento,
        "data_cancelamento": pedido.data_cancelamento,
        "tenant_id": pedido.tenant_id,
        "created_at": pedido.created_at,
        "updated_at": pedido.updated_at,
        "itens": [],
        "fornecedor_nome": None,
        "fornecedor_cnpj": None,
        "solicitacao_numero": None,
    }

    # Fornecedor
    if pedido.fornecedor:
        response["fornecedor_nome"] = pedido.fornecedor.razao_social
        response["fornecedor_cnpj"] = pedido.fornecedor.cnpj

    # Solicitacao
    if pedido.solicitacao_cotacao:
        response["solicitacao_numero"] = pedido.solicitacao_cotacao.numero

    # Itens
    for item in pedido.itens:
        item_data = {
            "id": item.id,
            "pedido_id": item.pedido_id,
            "produto_id": item.produto_id,
            "item_proposta_id": item.item_proposta_id,
            "quantidade": item.quantidade,
            "quantidade_recebida": item.quantidade_recebida,
            "unidade_medida": item.unidade_medida,
            "preco_unitario": item.preco_unitario,
            "desconto_percentual": item.desconto_percentual,
            "valor_total": item.valor_total,
            "especificacoes": item.especificacoes,
            "marca": item.marca,
            "prazo_entrega_item": item.prazo_entrega_item,
            "tenant_id": item.tenant_id,
            "created_at": item.created_at,
            "produto_nome": None,
            "produto_codigo": None,
        }
        if item.produto:
            item_data["produto_nome"] = item.produto.nome
            item_data["produto_codigo"] = item.produto.codigo
        response["itens"].append(item_data)

    return response


# ============ ROTAS CRUD ============

@router.get("/", response_model=PedidoCompraListResponse)
def listar_pedidos(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    fornecedor_id: Optional[int] = None,
    busca: Optional[str] = None
):
    """Listar pedidos de compra"""
    query = db.query(PedidoCompra).filter(
        PedidoCompra.tenant_id == tenant_id
    ).options(
        joinedload(PedidoCompra.fornecedor),
        joinedload(PedidoCompra.itens).joinedload(ItemPedido.produto),
        joinedload(PedidoCompra.solicitacao_cotacao)
    )

    if status:
        query = query.filter(PedidoCompra.status == status)
    if fornecedor_id:
        query = query.filter(PedidoCompra.fornecedor_id == fornecedor_id)
    if busca:
        # Busca em múltiplos campos: número do pedido, número da cotação, nome do fornecedor
        query = query.outerjoin(
            SolicitacaoCotacao,
            PedidoCompra.solicitacao_cotacao_id == SolicitacaoCotacao.id
        ).outerjoin(
            Fornecedor,
            PedidoCompra.fornecedor_id == Fornecedor.id
        ).filter(
            or_(
                PedidoCompra.numero.ilike(f"%{busca}%"),
                SolicitacaoCotacao.numero.ilike(f"%{busca}%"),
                Fornecedor.razao_social.ilike(f"%{busca}%"),
                Fornecedor.nome_fantasia.ilike(f"%{busca}%")
            )
        )

    return paginate_response(
        query, page, page_size,
        order_by=PedidoCompra.created_at.desc(),
        transform_fn=lambda p: _enrich_pedido_response(p, db)
    )


@router.get("/{pedido_id}", response_model=PedidoCompraResponse)
def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter pedido por ID"""
    pedido = get_by_id(
        db, PedidoCompra, pedido_id, tenant_id,
        error_message="Pedido nao encontrado",
        options=[
            joinedload(PedidoCompra.fornecedor),
            joinedload(PedidoCompra.itens).joinedload(ItemPedido.produto),
            joinedload(PedidoCompra.solicitacao_cotacao)
        ]
    )
    return _enrich_pedido_response(pedido, db)


@router.post("/", response_model=PedidoCompraResponse, status_code=201)
def criar_pedido(
    pedido_data: PedidoCompraCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Criar novo pedido de compra manualmente"""
    # Validar fornecedor e produtos usando helpers DRY
    validate_fk(db, Fornecedor, pedido_data.fornecedor_id, tenant_id, "Fornecedor")
    for item in pedido_data.itens:
        validate_fk(db, Produto, item.produto_id, tenant_id, f"Produto {item.produto_id}")

    # Criar pedido
    pedido = PedidoCompra(
        numero=gerar_numero_pedido(db, tenant_id),
        fornecedor_id=pedido_data.fornecedor_id,
        solicitacao_cotacao_id=pedido_data.solicitacao_cotacao_id,
        proposta_id=pedido_data.proposta_id,
        status=StatusPedido.RASCUNHO,
        condicoes_pagamento=pedido_data.condicoes_pagamento,
        prazo_entrega=pedido_data.prazo_entrega,
        frete_tipo=pedido_data.frete_tipo,
        valor_frete=pedido_data.valor_frete or 0,
        observacoes=pedido_data.observacoes,
        observacoes_internas=pedido_data.observacoes_internas,
        data_previsao_entrega=pedido_data.data_previsao_entrega,
        tenant_id=tenant_id,
        created_by=current_user.id
    )
    db.add(pedido)
    db.flush()

    # Criar itens
    for item_data in pedido_data.itens:
        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=item_data.produto_id,
            item_proposta_id=item_data.item_proposta_id,
            quantidade=item_data.quantidade,
            unidade_medida=item_data.unidade_medida,
            preco_unitario=item_data.preco_unitario,
            desconto_percentual=item_data.desconto_percentual,
            especificacoes=item_data.especificacoes,
            marca=item_data.marca,
            prazo_entrega_item=item_data.prazo_entrega_item,
            tenant_id=tenant_id
        )
        db.add(item)
        pedido.itens.append(item)

    # Calcular totais
    calcular_totais_pedido(pedido)
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.post("/from-cotacao", response_model=PedidoCompraResponse, status_code=201)
def criar_pedido_from_cotacao(
    data: PedidoCompraCreateFromCotacao,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Criar pedido a partir de uma proposta vencedora de cotacao

    Copia automaticamente:
    - Fornecedor
    - Condicoes de pagamento
    - Prazo de entrega
    - Itens com precos da proposta
    """
    # Buscar proposta usando helper
    proposta = get_by_id(
        db, PropostaFornecedor, data.proposta_id, tenant_id,
        error_message="Proposta nao encontrada",
        options=[
            joinedload(PropostaFornecedor.itens).joinedload(ItemProposta.item_solicitacao),
            joinedload(PropostaFornecedor.solicitacao)
        ]
    )

    if proposta.status != StatusProposta.VENCEDORA:
        raise HTTPException(status_code=400, detail="Apenas propostas vencedoras podem gerar pedidos")

    # Verificar se ja existe pedido para esta proposta
    pedido_existente = db.query(PedidoCompra).filter(
        PedidoCompra.proposta_id == proposta.id,
        PedidoCompra.tenant_id == tenant_id
    ).first()

    if pedido_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ja existe pedido {pedido_existente.numero} para esta proposta"
        )

    # Criar pedido
    pedido = PedidoCompra(
        numero=gerar_numero_pedido(db, tenant_id),
        fornecedor_id=proposta.fornecedor_id,
        solicitacao_cotacao_id=proposta.solicitacao_id,
        proposta_id=proposta.id,
        status=StatusPedido.RASCUNHO,
        condicoes_pagamento=proposta.condicoes_pagamento,
        prazo_entrega=proposta.prazo_entrega,
        frete_tipo=proposta.frete_tipo,
        valor_frete=proposta.frete_valor or 0,
        observacoes=data.observacoes,
        observacoes_internas=data.observacoes_internas,
        tenant_id=tenant_id,
        created_by=current_user.id
    )
    db.add(pedido)
    db.flush()

    # Criar itens a partir da proposta
    for item_proposta in proposta.itens:
        # Buscar produto do item de solicitacao
        if item_proposta.item_solicitacao:
            produto_id = item_proposta.item_solicitacao.produto_id
            quantidade = item_proposta.quantidade_disponivel or item_proposta.item_solicitacao.quantidade
            unidade = item_proposta.item_solicitacao.unidade_medida
            especificacoes = item_proposta.item_solicitacao.especificacoes
        else:
            continue

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto_id,
            item_proposta_id=item_proposta.id,
            quantidade=quantidade,
            unidade_medida=unidade,
            preco_unitario=item_proposta.preco_unitario,
            desconto_percentual=item_proposta.desconto_percentual,
            especificacoes=especificacoes,
            marca=item_proposta.marca_oferecida,
            prazo_entrega_item=item_proposta.prazo_entrega_item,
            tenant_id=tenant_id
        )
        db.add(item)
        pedido.itens.append(item)

    # Calcular totais
    calcular_totais_pedido(pedido)
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.put("/{pedido_id}", response_model=PedidoCompraResponse)
def atualizar_pedido(
    pedido_id: int,
    pedido_data: PedidoCompraUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Atualizar pedido (apenas em RASCUNHO)"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status != StatusPedido.RASCUNHO:
        raise HTTPException(status_code=400, detail="Apenas pedidos em rascunho podem ser editados")

    # Atualizar campos
    update_data = pedido_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pedido, key, value)

    calcular_totais_pedido(pedido)
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.delete("/{pedido_id}", status_code=204)
def excluir_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Excluir pedido (apenas em RASCUNHO)"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status != StatusPedido.RASCUNHO:
        raise HTTPException(status_code=400, detail="Apenas pedidos em rascunho podem ser excluidos")

    db.delete(pedido)
    db.commit()


# ============ ACOES ============

@router.post("/{pedido_id}/enviar-aprovacao", response_model=PedidoCompraResponse)
def enviar_para_aprovacao(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Enviar pedido para aprovacao"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status != StatusPedido.RASCUNHO:
        raise HTTPException(status_code=400, detail="Apenas pedidos em rascunho podem ser enviados")

    if len(pedido.itens) == 0:
        raise HTTPException(status_code=400, detail="Pedido deve ter pelo menos um item")

    pedido.status = StatusPedido.AGUARDANDO_APROVACAO
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.post("/{pedido_id}/aprovar", response_model=PedidoCompraResponse)
def aprovar_pedido(
    pedido_id: int,
    data: AprovarPedidoRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Aprovar pedido"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status != StatusPedido.AGUARDANDO_APROVACAO:
        raise HTTPException(status_code=400, detail="Pedido nao esta aguardando aprovacao")

    pedido.status = StatusPedido.APROVADO
    pedido.aprovado_por = current_user.id
    pedido.justificativa_aprovacao = data.justificativa
    pedido.data_aprovacao = datetime.utcnow()
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.post("/{pedido_id}/enviar-fornecedor", response_model=PedidoCompraResponse)
def enviar_para_fornecedor(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Enviar pedido ao fornecedor por email com PDF anexado"""
    from app.services.email_service import EmailService
    from app.services.pdf_service import PDFService
    from app.models.tenant import Tenant

    pedido = get_by_id(
        db, PedidoCompra, pedido_id, tenant_id,
        error_message="Pedido nao encontrado",
        options=[
            joinedload(PedidoCompra.fornecedor),
            joinedload(PedidoCompra.itens).joinedload(ItemPedido.produto)
        ]
    )

    if pedido.status != StatusPedido.APROVADO:
        raise HTTPException(status_code=400, detail="Pedido precisa estar aprovado")

    # Verificar se fornecedor tem email
    if not pedido.fornecedor or not pedido.fornecedor.email_principal:
        raise HTTPException(
            status_code=400,
            detail="Fornecedor nao possui email cadastrado"
        )

    # Buscar tenant para nome da empresa
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    # Preparar itens para email/PDF
    itens_email = []
    for item in pedido.itens:
        itens_email.append({
            'produto_nome': item.produto.nome if item.produto else 'N/A',
            'quantidade': float(item.quantidade),
            'unidade': item.unidade_medida or '',
            'preco_unitario': float(item.preco_unitario),
            'valor_total': float(item.valor_total),
            'especificacoes': item.especificacoes
        })

    # Gerar PDF da Ordem de Compra
    pdf_service = PDFService()
    pdf_bytes = pdf_service.gerar_ordem_compra_pdf(
        pedido_numero=pedido.numero,
        fornecedor_nome=pedido.fornecedor.razao_social or pedido.fornecedor.nome_fantasia,
        fornecedor_cnpj=pedido.fornecedor.cnpj,
        itens=itens_email,
        valor_total=float(pedido.valor_total or 0),
        prazo_entrega=pedido.prazo_entrega,
        condicao_pagamento=pedido.condicoes_pagamento,
        frete_tipo=pedido.frete_tipo,
        observacoes=pedido.observacoes,
        empresa_nome=tenant.nome_empresa if tenant else None,
        data_pedido=pedido.data_pedido
    )
    print(f"[PEDIDO] PDF gerado: {len(pdf_bytes)} bytes")

    # Enviar email com PDF anexado
    email_service = EmailService()

    sucesso = email_service.enviar_ordem_compra(
        fornecedor_email=pedido.fornecedor.email_principal,
        fornecedor_nome=pedido.fornecedor.razao_social or pedido.fornecedor.nome_fantasia,
        pedido_numero=pedido.numero,
        itens=itens_email,
        valor_total=float(pedido.valor_total or 0),
        prazo_entrega=pedido.prazo_entrega,
        condicao_pagamento=pedido.condicoes_pagamento,
        frete_tipo=pedido.frete_tipo,
        observacoes=pedido.observacoes,
        empresa_nome=tenant.nome_empresa if tenant else None,
        pdf_anexo=pdf_bytes
    )

    if not sucesso:
        raise HTTPException(
            status_code=500,
            detail="Falha ao enviar email para o fornecedor. Verifique configuracoes SMTP."
        )

    # Atualizar status
    pedido.status = StatusPedido.ENVIADO_FORNECEDOR
    pedido.data_envio = datetime.utcnow()
    db.commit()
    db.refresh(pedido)

    print(f"[PEDIDO] Email de OC {pedido.numero} com PDF enviado para {pedido.fornecedor.email_principal}")

    return _enrich_pedido_response(pedido, db)


@router.post("/{pedido_id}/confirmar", response_model=PedidoCompraResponse)
def confirmar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Registrar confirmacao do fornecedor"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status != StatusPedido.ENVIADO_FORNECEDOR:
        raise HTTPException(status_code=400, detail="Pedido precisa estar enviado ao fornecedor")

    pedido.status = StatusPedido.CONFIRMADO
    pedido.data_confirmacao = datetime.utcnow()
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.post("/{pedido_id}/cancelar", response_model=PedidoCompraResponse)
def cancelar_pedido(
    pedido_id: int,
    data: CancelarPedidoRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Cancelar pedido"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status in [StatusPedido.ENTREGUE, StatusPedido.CANCELADO]:
        raise HTTPException(status_code=400, detail="Pedido nao pode ser cancelado")

    pedido.status = StatusPedido.CANCELADO
    pedido.cancelado_por = current_user.id
    pedido.motivo_cancelamento = data.motivo
    pedido.data_cancelamento = datetime.utcnow()
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.post("/{pedido_id}/resetar-para-aprovado", response_model=PedidoCompraResponse)
def resetar_para_aprovado(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Resetar pedido para status APROVADO (para teste de envio de email)"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status not in [StatusPedido.ENVIADO_FORNECEDOR, StatusPedido.CONFIRMADO]:
        raise HTTPException(status_code=400, detail="Pedido precisa estar enviado ou confirmado")

    pedido.status = StatusPedido.APROVADO
    pedido.data_envio = None
    pedido.data_confirmacao = None
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)


@router.post("/{pedido_id}/registrar-entrega", response_model=PedidoCompraResponse)
def registrar_entrega(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Registrar entrega total do pedido"""
    pedido = get_by_id(db, PedidoCompra, pedido_id, tenant_id, error_message="Pedido nao encontrado")

    if pedido.status not in [StatusPedido.CONFIRMADO, StatusPedido.EM_TRANSITO, StatusPedido.ENTREGUE_PARCIAL]:
        raise HTTPException(status_code=400, detail="Pedido precisa estar confirmado ou em transito")

    # Marcar todos os itens como recebidos
    for item in pedido.itens:
        item.quantidade_recebida = item.quantidade

    pedido.status = StatusPedido.ENTREGUE
    pedido.data_entrega = datetime.utcnow()
    db.commit()
    db.refresh(pedido)

    return _enrich_pedido_response(pedido, db)
