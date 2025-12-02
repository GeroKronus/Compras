"""
Rotas de Cotações - Refatorado com DRY abstractions
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from app.api.deps import get_db, get_current_tenant_id, get_current_user
from app.models.cotacao import (
    SolicitacaoCotacao, ItemSolicitacao,
    PropostaFornecedor, ItemProposta,
    StatusSolicitacao, StatusProposta
)
from app.models.produto import Produto
from app.models.fornecedor import Fornecedor
from app.models.usuario import Usuario
from app.schemas.cotacao import (
    SolicitacaoCotacaoCreate, SolicitacaoCotacaoUpdate, SolicitacaoCotacaoResponse,
    SolicitacaoCotacaoListResponse, ItemSolicitacaoResponse,
    PropostaFornecedorCreate, PropostaFornecedorUpdate, PropostaFornecedorResponse,
    PropostaFornecedorListResponse, ItemPropostaResponse,
    EnviarSolicitacaoRequest, RegistrarPropostaRequest, EscolherVencedorRequest,
    MapaComparativoResponse, ItemMapaComparativo, SugestaoIAResponse,
    # Análise otimizada
    AnaliseOtimizadaResponse, AnaliseItemResponse, PrecoFornecedorItem,
    ResumoFornecedor, ItemOtimizado, CompraOtimizadaPorFornecedor,
    GerarOCsOtimizadasRequest, GerarOCsOtimizadasResponse, OCGerada
)
from app.api.utils import (
    get_by_id, validate_fk, paginate_query, apply_search_filter,
    update_entity, require_status, forbid_status, generate_sequential_number
)
from app.api.utils.sequencers import Prefixes
from app.models.produto_fornecedor import produto_fornecedor
from app.services.fornecedor_ranking_service import fornecedor_ranking_service

router = APIRouter()


# ============ SOLICITACOES DE COTACAO ============

@router.post("/solicitacoes", response_model=SolicitacaoCotacaoResponse, status_code=201)
def criar_solicitacao(
    solicitacao: SolicitacaoCotacaoCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Criar nova solicitacao de cotacao"""
    # Validar produtos e fornecedores
    for item in solicitacao.itens:
        validate_fk(db, Produto, item.produto_id, tenant_id, "Produto")
    for forn_id in solicitacao.fornecedores_ids:
        validate_fk(db, Fornecedor, forn_id, tenant_id, "Fornecedor")

    # Criar solicitacao
    db_solicitacao = SolicitacaoCotacao(
        numero=generate_sequential_number(db, SolicitacaoCotacao, Prefixes.SOLICITACAO_COTACAO, tenant_id),
        titulo=solicitacao.titulo,
        descricao=solicitacao.descricao,
        data_limite_proposta=solicitacao.data_limite_proposta,
        urgente=solicitacao.urgente,
        motivo_urgencia=solicitacao.motivo_urgencia,
        observacoes=solicitacao.observacoes,
        condicoes_pagamento_desejadas=solicitacao.condicoes_pagamento_desejadas,
        prazo_entrega_desejado=solicitacao.prazo_entrega_desejado,
        status=StatusSolicitacao.RASCUNHO,
        data_abertura=datetime.utcnow(),
        tenant_id=tenant_id,
        created_by=current_user.id
    )
    db.add(db_solicitacao)
    db.flush()

    # Criar itens
    for item in solicitacao.itens:
        db.add(ItemSolicitacao(
            solicitacao_id=db_solicitacao.id,
            produto_id=item.produto_id,
            quantidade=item.quantidade,
            unidade_medida=item.unidade_medida,
            especificacoes=item.especificacoes,
            tenant_id=tenant_id
        ))

    # Criar propostas vazias para fornecedores
    for forn_id in solicitacao.fornecedores_ids:
        db.add(PropostaFornecedor(
            solicitacao_id=db_solicitacao.id,
            fornecedor_id=forn_id,
            status=StatusProposta.PENDENTE,
            tenant_id=tenant_id,
            created_by=current_user.id
        ))

    db.commit()
    db.refresh(db_solicitacao)
    return _enrich_solicitacao_response(db_solicitacao, db)


@router.get("/solicitacoes", response_model=SolicitacaoCotacaoListResponse)
def listar_solicitacoes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[StatusSolicitacao] = None,
    busca: Optional[str] = None,
    urgente: Optional[bool] = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Listar solicitacoes com filtros"""
    query = db.query(SolicitacaoCotacao).filter(SolicitacaoCotacao.tenant_id == tenant_id)

    if status:
        query = query.filter(SolicitacaoCotacao.status == status)
    if busca:
        query = apply_search_filter(query, busca, SolicitacaoCotacao.numero, SolicitacaoCotacao.titulo)
    if urgente is not None:
        query = query.filter(SolicitacaoCotacao.urgente == urgente)

    items_raw, total = paginate_query(query, page, page_size, desc(SolicitacaoCotacao.created_at))
    items = [_enrich_solicitacao_response(s, db) for s in items_raw]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/solicitacoes/{solicitacao_id}", response_model=SolicitacaoCotacaoResponse)
def obter_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter detalhes de uma solicitacao"""
    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")
    return _enrich_solicitacao_response(solicitacao, db)


@router.put("/solicitacoes/{solicitacao_id}", response_model=SolicitacaoCotacaoResponse)
def atualizar_solicitacao(
    solicitacao_id: int,
    update: SolicitacaoCotacaoUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Atualizar solicitacao (apenas se RASCUNHO)"""
    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")
    require_status(solicitacao, [StatusSolicitacao.RASCUNHO], "editar")

    update_data = update.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user.id
    update_entity(db, solicitacao, update_data)
    return _enrich_solicitacao_response(solicitacao, db)


@router.post("/solicitacoes/{solicitacao_id}/enviar", response_model=SolicitacaoCotacaoResponse)
def enviar_solicitacao(
    solicitacao_id: int,
    request: EnviarSolicitacaoRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Enviar solicitacao para fornecedores (cria propostas e envia emails)"""
    from app.services.email_service import email_service

    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")
    require_status(solicitacao, [StatusSolicitacao.RASCUNHO, StatusSolicitacao.ENVIADA], "enviar")

    # Preparar dados dos itens para o email
    itens_email = []
    for item in solicitacao.itens:
        produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
        itens_email.append({
            "produto_nome": produto.nome if produto else f"Produto #{item.produto_id}",
            "quantidade": item.quantidade,
            "unidade_medida": item.unidade_medida or "UN",
            "especificacoes": item.especificacoes
        })

    # Data limite formatada para o email
    data_limite_str = None
    if solicitacao.data_limite_proposta:
        data_limite_str = solicitacao.data_limite_proposta.strftime('%d/%m/%Y')

    # Lista para rastrear emails enviados
    emails_enviados = []
    emails_falha = []

    for forn_id in request.fornecedores_ids:
        fornecedor = validate_fk(db, Fornecedor, forn_id, tenant_id, "Fornecedor")

        # Verificar se ja existe proposta
        proposta_existente = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id,
            PropostaFornecedor.fornecedor_id == forn_id,
            PropostaFornecedor.tenant_id == tenant_id
        ).first()

        if not proposta_existente:
            db.add(PropostaFornecedor(
                solicitacao_id=solicitacao_id,
                fornecedor_id=forn_id,
                status=StatusProposta.PENDENTE,
                data_envio_solicitacao=datetime.utcnow(),
                tenant_id=tenant_id,
                created_by=current_user.id
            ))
        else:
            proposta_existente.data_envio_solicitacao = datetime.utcnow()

        # Enviar email para o fornecedor se tiver email configurado
        if fornecedor.email_principal and email_service.is_configured:
            sucesso = email_service.enviar_solicitacao_cotacao_multiplos_itens(
                fornecedor_email=fornecedor.email_principal,
                fornecedor_nome=fornecedor.razao_social or fornecedor.nome_fantasia or "Fornecedor",
                solicitacao_numero=solicitacao.numero,
                solicitacao_titulo=solicitacao.titulo,
                itens=itens_email,
                observacoes=solicitacao.observacoes,
                solicitacao_id=solicitacao.id,
                data_limite=data_limite_str,
                fornecedor_cnpj=fornecedor.cnpj
            )
            if sucesso:
                emails_enviados.append(fornecedor.razao_social or fornecedor.nome_fantasia)
            else:
                emails_falha.append(fornecedor.razao_social or fornecedor.nome_fantasia)
        elif not fornecedor.email_principal:
            emails_falha.append(f"{fornecedor.razao_social or fornecedor.nome_fantasia} (sem email)")

    solicitacao.status = StatusSolicitacao.ENVIADA
    solicitacao.updated_by = current_user.id
    db.commit()
    db.refresh(solicitacao)

    # Log dos emails enviados
    print(f"[COTACAO] Solicitacao {solicitacao.numero} enviada para {len(emails_enviados)} fornecedor(es)")
    if emails_falha:
        print(f"[COTACAO] Falhas no envio: {emails_falha}")

    return _enrich_solicitacao_response(solicitacao, db)


@router.post("/solicitacoes/{solicitacao_id}/cancelar", response_model=SolicitacaoCotacaoResponse)
def cancelar_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Cancelar solicitacao"""
    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")
    forbid_status(solicitacao, [StatusSolicitacao.FINALIZADA], "cancelar")

    solicitacao.status = StatusSolicitacao.CANCELADA
    solicitacao.updated_by = current_user.id
    db.commit()
    db.refresh(solicitacao)
    return _enrich_solicitacao_response(solicitacao, db)


@router.delete("/solicitacoes/{solicitacao_id}", status_code=204)
def deletar_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Deletar solicitacao (apenas RASCUNHO)"""
    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")
    require_status(solicitacao, [StatusSolicitacao.RASCUNHO], "deletar")
    db.delete(solicitacao)
    db.commit()
    return None


@router.get("/solicitacoes/{solicitacao_id}/status-respostas")
def verificar_status_respostas(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Verifica o status de respostas de uma solicitacao de cotacao.

    Retorna:
    - Total de propostas enviadas
    - Quantidade respondida vs pendente
    - Tempo medio de resposta
    - Se pode finalizar (todas responderam ou prazo expirou)
    - Detalhes de cada proposta com tempo de resposta
    """
    # Verifica se pertence ao tenant
    get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

    return fornecedor_ranking_service.verificar_solicitacao_respondida(
        db=db,
        solicitacao_id=solicitacao_id
    )


@router.post("/propostas/{proposta_id}/registrar-recebimento")
def registrar_recebimento_proposta(
    proposta_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Registra o recebimento de uma proposta e atualiza estatisticas do fornecedor.

    Este endpoint e usado quando uma proposta e recebida (por email ou manualmente)
    para registrar o tempo de resposta e atualizar o ranking do fornecedor.

    Automaticamente:
    - Atualiza status da proposta para RECEBIDA
    - Calcula tempo de resposta (se data_envio_solicitacao existir)
    - Atualiza rating do fornecedor baseado no tempo de resposta
    - Atualiza status da solicitacao para EM_COTACAO se necessario
    """
    # Verifica se proposta pertence ao tenant
    proposta = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.id == proposta_id,
        PropostaFornecedor.tenant_id == tenant_id
    ).first()

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta nao encontrada")

    resultado = fornecedor_ranking_service.registrar_resposta_proposta(
        db=db,
        proposta_id=proposta_id
    )

    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])

    return resultado


# ============ PROPOSTAS ============

@router.get("/solicitacoes/{solicitacao_id}/propostas")
def listar_propostas_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Listar todas as propostas de uma solicitacao"""
    try:
        solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

        # Buscar propostas pela solicitacao (tenant validado via solicitacao)
        propostas = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id
        ).all()

        # Corrigir tenant_id das propostas automaticamente
        corrigidas = 0
        for p in propostas:
            if p.tenant_id != solicitacao.tenant_id:
                p.tenant_id = solicitacao.tenant_id
                corrigidas += 1
        if corrigidas > 0:
            db.commit()

        items = [_enrich_proposta_response(p, db) for p in propostas]
        return {"items": items, "total": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[ERRO] listar_propostas_solicitacao: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao listar propostas: {str(e)}")


@router.post("/propostas", response_model=PropostaFornecedorResponse, status_code=201)
def registrar_proposta(
    proposta: PropostaFornecedorCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Registrar proposta de um fornecedor"""
    solicitacao = get_by_id(db, SolicitacaoCotacao, proposta.solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")
    require_status(solicitacao, [StatusSolicitacao.ENVIADA, StatusSolicitacao.EM_COTACAO], "receber proposta")
    validate_fk(db, Fornecedor, proposta.fornecedor_id, tenant_id, "Fornecedor")

    # Buscar ou criar proposta
    db_proposta = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == proposta.solicitacao_id,
        PropostaFornecedor.fornecedor_id == proposta.fornecedor_id,
        PropostaFornecedor.tenant_id == tenant_id
    ).first()

    if db_proposta:
        require_status(db_proposta, [StatusProposta.PENDENTE, StatusProposta.RECEBIDA], "editar")
    else:
        db_proposta = PropostaFornecedor(
            solicitacao_id=proposta.solicitacao_id,
            fornecedor_id=proposta.fornecedor_id,
            tenant_id=tenant_id,
            created_by=current_user.id
        )
        db.add(db_proposta)
        db.flush()

    # Atualizar dados da proposta
    db_proposta.status = StatusProposta.RECEBIDA
    db_proposta.data_recebimento = datetime.utcnow()
    db_proposta.condicoes_pagamento = proposta.condicoes_pagamento
    db_proposta.prazo_entrega = proposta.prazo_entrega
    db_proposta.validade_proposta = proposta.validade_proposta
    db_proposta.frete_tipo = proposta.frete_tipo
    db_proposta.frete_valor = proposta.frete_valor
    db_proposta.observacoes = proposta.observacoes
    db_proposta.updated_by = current_user.id

    # Remover itens antigos
    db.query(ItemProposta).filter(ItemProposta.proposta_id == db_proposta.id).delete()

    # Criar itens da proposta
    valor_total = Decimal('0')
    for item in proposta.itens:
        item_solic = db.query(ItemSolicitacao).filter(
            ItemSolicitacao.id == item.item_solicitacao_id,
            ItemSolicitacao.solicitacao_id == proposta.solicitacao_id
        ).first()
        if not item_solic:
            raise HTTPException(status_code=404, detail=f"Item de solicitacao {item.item_solicitacao_id} nao encontrado")

        qtd = item.quantidade_disponivel or item_solic.quantidade
        preco_final = item.preco_unitario * qtd * (1 - item.desconto_percentual / 100)
        valor_total += preco_final

        db.add(ItemProposta(
            proposta_id=db_proposta.id,
            item_solicitacao_id=item.item_solicitacao_id,
            preco_unitario=item.preco_unitario,
            quantidade_disponivel=item.quantidade_disponivel,
            desconto_percentual=item.desconto_percentual,
            preco_final=preco_final,
            prazo_entrega_item=item.prazo_entrega_item,
            observacoes=item.observacoes,
            marca_oferecida=item.marca_oferecida,
            tenant_id=tenant_id
        ))

    if db_proposta.frete_valor:
        valor_total += db_proposta.frete_valor
    db_proposta.valor_total = valor_total

    if solicitacao.status == StatusSolicitacao.ENVIADA:
        solicitacao.status = StatusSolicitacao.EM_COTACAO

    db.commit()
    db.refresh(db_proposta)
    return _enrich_proposta_response(db_proposta, db)


@router.get("/propostas/{proposta_id}", response_model=PropostaFornecedorResponse)
def obter_proposta(
    proposta_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter detalhes de uma proposta"""
    proposta = get_by_id(db, PropostaFornecedor, proposta_id, tenant_id, error_message="Proposta nao encontrada")
    return _enrich_proposta_response(proposta, db)


@router.put("/propostas/{proposta_id}", response_model=PropostaFornecedorResponse)
def atualizar_proposta(
    proposta_id: int,
    update: PropostaFornecedorUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Atualizar dados de uma proposta manualmente"""
    proposta = get_by_id(db, PropostaFornecedor, proposta_id, tenant_id, error_message="Proposta nao encontrada")

    # Atualizar campos
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(proposta, field):
            setattr(proposta, field, value)

    proposta.updated_by = current_user.id
    db.commit()
    db.refresh(proposta)
    return _enrich_proposta_response(proposta, db)


@router.post("/solicitacoes/{solicitacao_id}/escolher-vencedor", response_model=SolicitacaoCotacaoResponse)
def escolher_vencedor(
    solicitacao_id: int,
    request: EscolherVencedorRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """Escolher proposta vencedora"""
    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")
    # Permitir escolher vencedor em ENVIADA (propostas manuais) ou EM_COTACAO (propostas via email)
    require_status(solicitacao, [StatusSolicitacao.EM_COTACAO, StatusSolicitacao.ENVIADA], "escolher vencedor")

    proposta_vencedora = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.id == request.proposta_id,
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.tenant_id == tenant_id
    ).first()
    if not proposta_vencedora:
        raise HTTPException(status_code=404, detail="Proposta nao encontrada")
    require_status(proposta_vencedora, [StatusProposta.RECEBIDA], "selecionar como vencedora")

    # Verificar se a escolha diverge da proposta de menor preço (recomendada)
    # Buscar proposta com menor valor total entre as recebidas
    proposta_menor_preco = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.status == StatusProposta.RECEBIDA,
        PropostaFornecedor.tenant_id == tenant_id,
        PropostaFornecedor.valor_total.isnot(None)
    ).order_by(PropostaFornecedor.valor_total.asc()).first()

    # Registrar auditoria se a escolha for diferente da proposta de menor preço
    if proposta_menor_preco and proposta_menor_preco.id != proposta_vencedora.id:
        from app.models.auditoria_escolha import AuditoriaEscolhaFornecedor
        from decimal import Decimal

        # Buscar nomes dos fornecedores
        fornecedor_escolhido = db.query(Fornecedor).filter(
            Fornecedor.id == proposta_vencedora.fornecedor_id
        ).first()
        fornecedor_recomendado = db.query(Fornecedor).filter(
            Fornecedor.id == proposta_menor_preco.fornecedor_id
        ).first()

        valor_escolhido = Decimal(str(proposta_vencedora.valor_total or 0))
        valor_recomendado = Decimal(str(proposta_menor_preco.valor_total or 0))
        diferenca = valor_escolhido - valor_recomendado
        diferenca_percentual = (diferenca / valor_recomendado * 100) if valor_recomendado > 0 else Decimal('0')

        auditoria = AuditoriaEscolhaFornecedor(
            tenant_id=tenant_id,
            solicitacao_id=solicitacao_id,
            solicitacao_numero=solicitacao.numero,
            proposta_escolhida_id=proposta_vencedora.id,
            fornecedor_escolhido_nome=fornecedor_escolhido.razao_social if fornecedor_escolhido else "N/A",
            valor_escolhido=valor_escolhido,
            proposta_recomendada_id=proposta_menor_preco.id,
            fornecedor_recomendado_nome=fornecedor_recomendado.razao_social if fornecedor_recomendado else "N/A",
            valor_recomendado=valor_recomendado,
            diferenca_valor=diferenca,
            diferenca_percentual=diferenca_percentual,
            justificativa=request.justificativa or "Não informada",
            usuario_id=current_user.id,
            usuario_nome=current_user.nome,
            data_escolha=datetime.utcnow()
        )
        db.add(auditoria)
        print(f"[AUDITORIA] Escolha divergente registrada: {solicitacao.numero} - Diferença: R$ {diferenca:.2f} ({diferenca_percentual:.1f}%)")

    # Marcar vencedora e rejeitar demais
    proposta_vencedora.status = StatusProposta.VENCEDORA
    db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.id != request.proposta_id,
        PropostaFornecedor.status == StatusProposta.RECEBIDA,
        PropostaFornecedor.tenant_id == tenant_id
    ).update({"status": StatusProposta.REJEITADA})

    solicitacao.status = StatusSolicitacao.FINALIZADA
    solicitacao.proposta_vencedora_id = request.proposta_id
    solicitacao.justificativa_escolha = request.justificativa
    solicitacao.data_fechamento = datetime.utcnow()
    solicitacao.updated_by = current_user.id

    db.commit()
    db.refresh(solicitacao)

    # Enviar email de notificação ao fornecedor vencedor
    try:
        from app.services.email_service import email_service

        if email_service.is_configured:
            # Buscar dados do fornecedor
            fornecedor = db.query(Fornecedor).filter(
                Fornecedor.id == proposta_vencedora.fornecedor_id
            ).first()

            if fornecedor and fornecedor.email_principal:
                # Buscar itens da proposta
                itens_proposta = db.query(ItemProposta).filter(
                    ItemProposta.proposta_id == proposta_vencedora.id
                ).all()

                # Montar lista de itens para o email
                itens_email = []
                for item_proposta in itens_proposta:
                    # Buscar o item da solicitação para pegar o nome do produto
                    item_solic = db.query(ItemSolicitacao).filter(
                        ItemSolicitacao.id == item_proposta.item_solicitacao_id
                    ).first()

                    produto_nome = "N/A"
                    if item_solic:
                        produto = db.query(Produto).filter(
                            Produto.id == item_solic.produto_id
                        ).first()
                        if produto:
                            produto_nome = produto.nome

                    itens_email.append({
                        'produto_nome': produto_nome,
                        'quantidade': float(item_proposta.quantidade_disponivel or 0),
                        'preco_unitario': float(item_proposta.preco_unitario or 0),
                        'preco_total': float(item_proposta.preco_final or 0)
                    })

                # Enviar email
                email_service.enviar_notificacao_vencedor(
                    fornecedor_email=fornecedor.email_principal,
                    fornecedor_nome=fornecedor.razao_social or fornecedor.nome_fantasia,
                    solicitacao_numero=solicitacao.numero,
                    solicitacao_titulo=solicitacao.titulo or f"Cotação {solicitacao.numero}",
                    itens=itens_email,
                    valor_total=float(proposta_vencedora.valor_total or 0),
                    prazo_entrega=proposta_vencedora.prazo_entrega,
                    condicao_pagamento=proposta_vencedora.condicao_pagamento
                )
                print(f"[COTACAO] Email de vencedor enviado para {fornecedor.email_principal}")
    except Exception as e:
        # Não falha a operação se o email não for enviado
        print(f"[COTACAO] Erro ao enviar email de vencedor: {e}")

    return _enrich_solicitacao_response(solicitacao, db)


# ============ MAPA COMPARATIVO ============

@router.get("/solicitacoes/{solicitacao_id}/mapa-comparativo")
def obter_mapa_comparativo(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Gerar mapa comparativo de propostas - v2 com proposta_id"""
    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

    itens_solicitacao = db.query(ItemSolicitacao).filter(ItemSolicitacao.solicitacao_id == solicitacao_id).all()
    # Buscar propostas pela solicitacao (tenant ja validado via solicitacao)
    propostas = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.status.in_([StatusProposta.RECEBIDA, StatusProposta.VENCEDORA])
    ).all()

    itens_mapa = []
    resumo_fornecedores = {}

    for item_solic in itens_solicitacao:
        produto = db.query(Produto).filter(Produto.id == item_solic.produto_id).first()
        item_map = {
            "item_solicitacao_id": item_solic.id,
            "produto_id": item_solic.produto_id,
            "produto_nome": produto.nome if produto else "N/A",
            "produto_codigo": produto.codigo if produto else "N/A",
            "quantidade_solicitada": item_solic.quantidade,
            "propostas": []
        }

        for proposta in propostas:
            fornecedor = db.query(Fornecedor).filter(Fornecedor.id == proposta.fornecedor_id).first()
            item_proposta = db.query(ItemProposta).filter(
                ItemProposta.proposta_id == proposta.id,
                ItemProposta.item_solicitacao_id == item_solic.id
            ).first()

            if item_proposta:
                item_map["propostas"].append({
                    "proposta_id": proposta.id,
                    "fornecedor_id": proposta.fornecedor_id,
                    "fornecedor_nome": fornecedor.razao_social if fornecedor else "N/A",
                    "fornecedor_cnpj": fornecedor.cnpj if fornecedor else "",
                    "preco_unitario": float(item_proposta.preco_unitario),
                    "quantidade_disponivel": float(item_proposta.quantidade_disponivel or 0),
                    "desconto_percentual": float(item_proposta.desconto_percentual or 0),
                    "preco_final": float(item_proposta.preco_final or 0),
                    "prazo_entrega_item": item_proposta.prazo_entrega_item,
                    "marca_oferecida": item_proposta.marca_oferecida
                })

                if proposta.id not in resumo_fornecedores:
                    resumo_fornecedores[proposta.id] = {
                        "fornecedor_nome": fornecedor.razao_social if fornecedor else "N/A",
                        "fornecedor_cnpj": fornecedor.cnpj if fornecedor else "",
                        "valor_total": float(proposta.valor_total or 0),
                        "itens_cotados": 1,
                        "prazo_medio": proposta.prazo_entrega or 0
                    }
                else:
                    resumo_fornecedores[proposta.id]["itens_cotados"] += 1

        itens_mapa.append(item_map)

    return {
        "solicitacao_id": solicitacao_id,
        "solicitacao_numero": solicitacao.numero,
        "solicitacao_titulo": solicitacao.titulo,
        "itens": itens_mapa,
        "resumo": resumo_fornecedores
    }


# ============ SUGESTAO IA ============

@router.get("/solicitacoes/{solicitacao_id}/sugestao-ia", response_model=SugestaoIAResponse)
def obter_sugestao_ia(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter sugestao de melhor proposta baseada em criterios"""
    get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

    propostas = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.status == StatusProposta.RECEBIDA,
        PropostaFornecedor.tenant_id == tenant_id
    ).all()

    if len(propostas) < 2:
        raise HTTPException(status_code=400, detail="Necessario pelo menos 2 propostas para sugestao")

    valores = [float(p.valor_total or 0) for p in propostas]
    prazos = [p.prazo_entrega or 999 for p in propostas]
    min_valor, max_valor = min(valores) or 1, max(valores) or 1
    min_prazo, max_prazo = min(prazos) or 1, max(prazos) or 1

    melhor_proposta, melhor_score = None, -1
    motivos, alertas = [], []

    for proposta in propostas:
        valor = float(proposta.valor_total or 0)
        prazo = proposta.prazo_entrega or 999

        score_preco = 5 * (1 - (valor - min_valor) / (max_valor - min_valor)) if max_valor > min_valor else 5
        score_prazo = 5 * (1 - (prazo - min_prazo) / (max_prazo - min_prazo)) if max_prazo > min_prazo else 5

        score_condicoes = 3.5
        if proposta.condicoes_pagamento and "30" in proposta.condicoes_pagamento:
            score_condicoes += 1
        if proposta.frete_tipo == "CIF":
            score_condicoes += 0.5

        score_total = (score_preco * 0.5) + (score_prazo * 0.3) + (score_condicoes * 0.2)

        proposta.score_preco = round(score_preco, 2)
        proposta.score_prazo = round(score_prazo, 2)
        proposta.score_condicoes = round(score_condicoes, 2)
        proposta.score_total = round(score_total, 2)

        if score_total > melhor_score:
            melhor_score = score_total
            melhor_proposta = proposta

    db.commit()

    if not melhor_proposta:
        raise HTTPException(status_code=400, detail="Nao foi possivel calcular sugestao")

    fornecedor = db.query(Fornecedor).filter(Fornecedor.id == melhor_proposta.fornecedor_id).first()

    if melhor_proposta.score_preco >= 4:
        motivos.append("Melhor preco entre as propostas")
    if melhor_proposta.score_prazo >= 4:
        motivos.append("Prazo de entrega competitivo")
    if melhor_proposta.score_condicoes >= 4:
        motivos.append("Boas condicoes de pagamento")
    if not motivos:
        motivos.append("Melhor equilibrio entre preco, prazo e condicoes")

    economia = None
    if len(valores) > 1:
        segundo_menor = sorted(valores)[1]
        economia = round(segundo_menor - float(melhor_proposta.valor_total or 0), 2)
        if economia > 0:
            motivos.append(f"Economia de R$ {economia:.2f} em relacao a segunda melhor")

    if melhor_proposta.prazo_entrega and melhor_proposta.prazo_entrega > 30:
        alertas.append("Prazo de entrega superior a 30 dias")
    if melhor_proposta.validade_proposta:
        dias_validade = (melhor_proposta.validade_proposta - date.today()).days
        if dias_validade < 7:
            alertas.append(f"Proposta expira em {dias_validade} dias")

    return {
        "proposta_sugerida_id": melhor_proposta.id,
        "fornecedor_nome": fornecedor.razao_social if fornecedor else "N/A",
        "score_total": melhor_proposta.score_total,
        "motivos": motivos,
        "economia_estimada": economia,
        "alertas": alertas
    }


@router.get("/solicitacoes/{solicitacao_id}/sugestao-claude")
def obter_sugestao_claude(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter sugestao usando Claude AI (Anthropic)

    Analise mais sofisticada com IA generativa.
    Requer ANTHROPIC_API_KEY configurada no .env
    """
    from app.services.ai_service import ai_service

    if not ai_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="API da Anthropic nao configurada. Adicione ANTHROPIC_API_KEY no arquivo .env"
        )

    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

    propostas = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.status == StatusProposta.RECEBIDA,
        PropostaFornecedor.tenant_id == tenant_id
    ).all()

    if len(propostas) < 2:
        raise HTTPException(status_code=400, detail="Necessario pelo menos 2 propostas para analise")

    # Preparar dados para IA
    solicitacao_dict = {
        "id": solicitacao.id,
        "numero": solicitacao.numero,
        "titulo": solicitacao.titulo,
        "urgente": solicitacao.urgente,
        "prazo_entrega_desejado": solicitacao.prazo_entrega_desejado,
        "condicoes_pagamento_desejadas": solicitacao.condicoes_pagamento_desejadas
    }

    propostas_dict = []
    for proposta in propostas:
        fornecedor = db.query(Fornecedor).filter(Fornecedor.id == proposta.fornecedor_id).first()

        itens_dict = []
        for item in proposta.itens:
            item_solic = db.query(ItemSolicitacao).filter(ItemSolicitacao.id == item.item_solicitacao_id).first()
            produto = db.query(Produto).filter(Produto.id == item_solic.produto_id).first() if item_solic else None

            itens_dict.append({
                "produto_nome": produto.nome if produto else "N/A",
                "preco_unitario": float(item.preco_unitario or 0),
                "quantidade_disponivel": item.quantidade_disponivel,
                "desconto_percentual": float(item.desconto_percentual or 0),
                "preco_final": float(item.preco_final or 0)
            })

        propostas_dict.append({
            "id": proposta.id,
            "fornecedor_nome": fornecedor.razao_social if fornecedor else "N/A",
            "valor_total": float(proposta.valor_total or 0),
            "prazo_entrega": proposta.prazo_entrega,
            "condicoes_pagamento": proposta.condicoes_pagamento,
            "frete_tipo": proposta.frete_tipo,
            "frete_valor": float(proposta.frete_valor or 0),
            "validade_proposta": str(proposta.validade_proposta) if proposta.validade_proposta else None,
            "itens": itens_dict
        })

    # Chamar IA com registro de uso
    resultado = ai_service.analisar_propostas_com_registro(
        db=db,
        tenant_id=tenant_id,
        solicitacao=solicitacao_dict,
        propostas=propostas_dict,
        usuario_id=current_user.id
    )

    if "error" in resultado:
        raise HTTPException(status_code=500, detail=resultado["error"])

    return resultado


# ============ HELPERS ============

def _enrich_solicitacao_response(solicitacao: SolicitacaoCotacao, db: Session) -> dict:
    """Enriquecer resposta com dados relacionados"""
    itens = []
    for item in solicitacao.itens:
        produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
        itens.append({
            "id": item.id, "solicitacao_id": item.solicitacao_id, "produto_id": item.produto_id,
            "quantidade": item.quantidade, "unidade_medida": item.unidade_medida,
            "especificacoes": item.especificacoes, "tenant_id": item.tenant_id, "created_at": item.created_at,
            "produto_nome": produto.nome if produto else None, "produto_codigo": produto.codigo if produto else None
        })

    total_propostas = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao.id,
        PropostaFornecedor.tenant_id == solicitacao.tenant_id
    ).count()

    return {
        "id": solicitacao.id, "numero": solicitacao.numero, "titulo": solicitacao.titulo,
        "descricao": solicitacao.descricao, "status": solicitacao.status, "data_abertura": solicitacao.data_abertura,
        "data_limite_proposta": solicitacao.data_limite_proposta, "data_fechamento": solicitacao.data_fechamento,
        "urgente": solicitacao.urgente, "motivo_urgencia": solicitacao.motivo_urgencia,
        "observacoes": solicitacao.observacoes, "condicoes_pagamento_desejadas": solicitacao.condicoes_pagamento_desejadas,
        "prazo_entrega_desejado": solicitacao.prazo_entrega_desejado, "proposta_vencedora_id": solicitacao.proposta_vencedora_id,
        "justificativa_escolha": solicitacao.justificativa_escolha, "tenant_id": solicitacao.tenant_id,
        "created_at": solicitacao.created_at, "updated_at": solicitacao.updated_at,
        "itens": itens, "total_propostas": total_propostas
    }


def _enrich_proposta_response(proposta: PropostaFornecedor, db: Session) -> dict:
    """Enriquecer resposta de proposta"""
    fornecedor = db.query(Fornecedor).filter(Fornecedor.id == proposta.fornecedor_id).first()

    itens = []
    for item in proposta.itens:
        item_solic = db.query(ItemSolicitacao).filter(ItemSolicitacao.id == item.item_solicitacao_id).first()
        produto = db.query(Produto).filter(Produto.id == item_solic.produto_id).first() if item_solic else None

        itens.append({
            "id": item.id, "proposta_id": item.proposta_id, "item_solicitacao_id": item.item_solicitacao_id,
            "preco_unitario": item.preco_unitario, "quantidade_disponivel": item.quantidade_disponivel,
            "desconto_percentual": item.desconto_percentual, "preco_final": item.preco_final,
            "prazo_entrega_item": item.prazo_entrega_item, "observacoes": item.observacoes,
            "marca_oferecida": item.marca_oferecida, "tenant_id": item.tenant_id, "created_at": item.created_at,
            "produto_nome": produto.nome if produto else None,
            "quantidade_solicitada": item_solic.quantidade if item_solic else None
        })

    return {
        "id": proposta.id, "solicitacao_id": proposta.solicitacao_id, "fornecedor_id": proposta.fornecedor_id,
        "status": proposta.status, "data_envio_solicitacao": proposta.data_envio_solicitacao,
        "data_recebimento": proposta.data_recebimento, "condicoes_pagamento": proposta.condicoes_pagamento,
        "prazo_entrega": proposta.prazo_entrega, "validade_proposta": proposta.validade_proposta,
        "valor_total": proposta.valor_total, "desconto_total": proposta.desconto_total or 0,
        "frete_tipo": proposta.frete_tipo, "frete_valor": proposta.frete_valor, "observacoes": proposta.observacoes,
        "score_preco": proposta.score_preco, "score_prazo": proposta.score_prazo,
        "score_condicoes": proposta.score_condicoes, "score_total": proposta.score_total,
        "tenant_id": proposta.tenant_id, "created_at": proposta.created_at, "updated_at": proposta.updated_at,
        "itens": itens, "fornecedor_nome": fornecedor.razao_social if fornecedor else None,
        "fornecedor_cnpj": fornecedor.cnpj if fornecedor else None
    }


# ============ TESTE DE EMAIL ============

@router.post("/teste-email")
def testar_envio_email(
    email_destino: str,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Endpoint para testar se o servico de email esta funcionando.
    Envia um email de teste para o endereco informado.
    """
    from app.services.email_service import email_service

    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Servico de email nao configurado. Verifique SMTP_USER e SMTP_PASSWORD no .env"
        )

    corpo_html = """
    <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 500px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0;">Teste de Email</h1>
        </div>
        <div style="background: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px;">
            <p>Este e um email de teste do Sistema de Gestao de Compras.</p>
            <p>Se voce esta recebendo esta mensagem, o servico de email esta funcionando corretamente!</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #666; font-size: 12px;">Email enviado automaticamente para fins de teste.</p>
        </div>
    </div>
    """

    sucesso = email_service.enviar_email(
        destinatario=email_destino,
        assunto="[TESTE] Sistema de Gestao de Compras",
        corpo_html=corpo_html,
        corpo_texto="Este e um email de teste do Sistema de Gestao de Compras. Se voce esta recebendo esta mensagem, o servico esta funcionando!"
    )

    if sucesso:
        return {
            "sucesso": True,
            "mensagem": f"Email de teste enviado com sucesso para {email_destino}",
            "email_destino": email_destino
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao enviar email para {email_destino}. Verifique as configuracoes SMTP."
        )


# ============ COTACAO POR EMAIL ============

@router.post("/solicitar-por-email")
def solicitar_cotacao_por_email(
    produto_id: int,
    quantidade: int,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Solicitar cotacao por email para um produto.

    1. Busca fornecedores cadastrados para o produto
    2. Cria solicitacao de cotacao
    3. Envia emails para os fornecedores
    4. Retorna status do envio
    """
    from app.services.email_service import email_service

    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Servico de email nao configurado. Adicione SMTP_USER e SMTP_PASSWORD no .env"
        )

    # Buscar produto
    produto = get_by_id(db, Produto, produto_id, tenant_id, error_message="Produto nao encontrado")

    # Buscar APENAS os fornecedores associados ao produto
    fornecedores = db.query(Fornecedor).join(
        produto_fornecedor,
        Fornecedor.id == produto_fornecedor.c.fornecedor_id
    ).filter(
        produto_fornecedor.c.produto_id == produto_id,
        produto_fornecedor.c.tenant_id == tenant_id,
        Fornecedor.ativo == True,
        Fornecedor.email_principal.isnot(None),
        Fornecedor.email_principal != ""
    ).all()

    if not fornecedores:
        raise HTTPException(
            status_code=400,
            detail="Nenhum fornecedor cadastrado para este produto. Adicione fornecedores ao produto antes de solicitar cotacao."
        )

    # Criar solicitacao de cotacao
    db_solicitacao = SolicitacaoCotacao(
        numero=generate_sequential_number(db, SolicitacaoCotacao, Prefixes.SOLICITACAO_COTACAO, tenant_id),
        titulo=f"Cotacao: {produto.nome}",
        descricao=observacoes or f"Solicitacao de cotacao para {quantidade} {produto.unidade_medida or 'un'} de {produto.nome}",
        status=StatusSolicitacao.ENVIADA,
        data_abertura=datetime.utcnow(),
        tenant_id=tenant_id,
        created_by=current_user.id
    )
    db.add(db_solicitacao)
    db.flush()

    # Criar item da solicitacao
    db.add(ItemSolicitacao(
        solicitacao_id=db_solicitacao.id,
        produto_id=produto_id,
        quantidade=quantidade,
        unidade_medida=produto.unidade_medida or "un",
        tenant_id=tenant_id
    ))

    # Enviar emails e criar propostas
    emails_enviados = []
    emails_falha = []

    for fornecedor in fornecedores:
        # Criar proposta pendente
        db.add(PropostaFornecedor(
            solicitacao_id=db_solicitacao.id,
            fornecedor_id=fornecedor.id,
            status=StatusProposta.PENDENTE,
            data_envio_solicitacao=datetime.utcnow(),
            tenant_id=tenant_id,
            created_by=current_user.id
        ))

        # Enviar email
        sucesso = email_service.enviar_solicitacao_cotacao(
            fornecedor_email=fornecedor.email_principal,
            fornecedor_nome=fornecedor.razao_social or fornecedor.nome_fantasia,
            produto_nome=produto.nome,
            quantidade=quantidade,
            unidade=produto.unidade_medida or "un",
            observacoes=observacoes,
            solicitacao_id=db_solicitacao.id
        )

        if sucesso:
            emails_enviados.append(fornecedor.razao_social or fornecedor.nome_fantasia)
        else:
            emails_falha.append(fornecedor.razao_social or fornecedor.nome_fantasia)

    db.commit()
    db.refresh(db_solicitacao)

    return {
        "solicitacao_id": db_solicitacao.id,
        "solicitacao_numero": db_solicitacao.numero,
        "produto": produto.nome,
        "quantidade": quantidade,
        "emails_enviados": len(emails_enviados),
        "fornecedores_notificados": emails_enviados,
        "falhas": emails_falha,
        "status": "AGUARDANDO_RESPOSTAS",
        "mensagem": f"Emails enviados para {len(emails_enviados)} fornecedor(es). Aguardando respostas."
    }


@router.post("/solicitacoes/{solicitacao_id}/verificar-respostas")
def verificar_respostas_email(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Verificar respostas de email para uma solicitacao.

    1. Le a caixa de entrada
    2. Busca emails relacionados a solicitacao
    3. Usa Claude para extrair dados das propostas
    4. Retorna propostas encontradas
    """
    from app.services.email_service import email_service
    from app.services.ai_service import ai_service

    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Servico de email nao configurado"
        )

    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

    # Ler emails relacionados
    emails = email_service.ler_emails_cotacao(solicitacao_id)

    if not emails:
        return {
            "solicitacao_id": solicitacao_id,
            "emails_encontrados": 0,
            "propostas_extraidas": [],
            "mensagem": "Nenhuma resposta encontrada ainda. Tente novamente mais tarde."
        }

    propostas_extraidas = []

    for email_data in emails:
        # Tentar identificar fornecedor pelo email
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.tenant_id == tenant_id,
            Fornecedor.email == email_data['email_remetente']
        ).first()

        proposta_info = {
            "email_remetente": email_data['email_remetente'],
            "fornecedor_identificado": fornecedor.razao_social if fornecedor else None,
            "data_recebimento": email_data['data'],
            "corpo_email": email_data['corpo'][:500] + "..." if len(email_data['corpo']) > 500 else email_data['corpo']
        }

        # Se tiver Claude disponivel, usar para extrair dados (com registro de uso)
        if ai_service.is_available:
            dados_extraidos = ai_service.extrair_dados_email_com_registro(
                db=db,
                tenant_id=tenant_id,
                corpo_email=email_data['corpo'],
                usuario_id=current_user.id
            )
            proposta_info["dados_extraidos"] = dados_extraidos

        propostas_extraidas.append(proposta_info)

    return {
        "solicitacao_id": solicitacao_id,
        "solicitacao_numero": solicitacao.numero,
        "emails_encontrados": len(emails),
        "propostas_extraidas": propostas_extraidas,
        "mensagem": f"Encontrados {len(emails)} email(s) de resposta. Revise os dados extraidos."
    }


# ============ ANÁLISE OTIMIZADA POR ITEM ============

@router.get("/solicitacoes/{solicitacao_id}/analise-otimizada", response_model=AnaliseOtimizadaResponse)
def obter_analise_otimizada(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Análise otimizada de propostas com comparativo por item.

    Retorna:
    - Matriz item × fornecedor com destaque do menor preço por item
    - Comparativo: compra única vs compra otimizada (split)
    - Economia potencial ao desmembrar entre fornecedores
    - Recomendação automática
    """
    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

    # Buscar itens da solicitação
    itens_solicitacao = db.query(ItemSolicitacao).filter(
        ItemSolicitacao.solicitacao_id == solicitacao_id
    ).all()

    if not itens_solicitacao:
        raise HTTPException(status_code=400, detail="Solicitacao sem itens")

    # Buscar propostas recebidas
    propostas = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.status.in_([StatusProposta.RECEBIDA, StatusProposta.VENCEDORA])
    ).all()

    if len(propostas) < 1:
        raise HTTPException(status_code=400, detail="Nenhuma proposta recebida para analise")

    # Mapear fornecedores e propostas
    fornecedores_map = {}
    propostas_map = {}
    for proposta in propostas:
        fornecedor = db.query(Fornecedor).filter(Fornecedor.id == proposta.fornecedor_id).first()
        fornecedores_map[proposta.fornecedor_id] = fornecedor
        propostas_map[proposta.fornecedor_id] = proposta

    # Construir análise por item
    itens_analise = []
    melhor_por_item = {}  # {item_solicitacao_id: {fornecedor_id, preco_total, item_proposta_id, ...}}

    for item_solic in itens_solicitacao:
        produto = db.query(Produto).filter(Produto.id == item_solic.produto_id).first()

        precos_fornecedores = []
        menor_preco_total = None
        fornecedor_menor_id = None
        fornecedor_menor_nome = None
        menor_preco_unitario = None

        for proposta in propostas:
            # Buscar item da proposta correspondente
            item_proposta = db.query(ItemProposta).filter(
                ItemProposta.proposta_id == proposta.id,
                ItemProposta.item_solicitacao_id == item_solic.id
            ).first()

            if not item_proposta:
                continue

            fornecedor = fornecedores_map.get(proposta.fornecedor_id)
            if not fornecedor:
                continue

            # Calcular preço final
            preco_unitario = float(item_proposta.preco_unitario or 0)
            desconto = float(item_proposta.desconto_percentual or 0)
            preco_final = preco_unitario * (1 - desconto / 100)
            quantidade = float(item_solic.quantidade)
            preco_total = preco_final * quantidade

            preco_info = PrecoFornecedorItem(
                fornecedor_id=proposta.fornecedor_id,
                fornecedor_nome=fornecedor.razao_social,
                proposta_id=proposta.id,
                item_proposta_id=item_proposta.id,
                preco_unitario=Decimal(str(preco_unitario)),
                desconto_percentual=Decimal(str(desconto)),
                preco_final=Decimal(str(round(preco_final, 2))),
                preco_total=Decimal(str(round(preco_total, 2))),
                prazo_entrega=item_proposta.prazo_entrega_item or proposta.prazo_entrega,
                condicoes_pagamento=proposta.condicoes_pagamento,
                marca_oferecida=item_proposta.marca_oferecida,
                is_menor_preco=False
            )
            precos_fornecedores.append(preco_info)

            # Verificar se é menor preço
            if menor_preco_total is None or preco_total < menor_preco_total:
                menor_preco_total = preco_total
                menor_preco_unitario = preco_final
                fornecedor_menor_id = proposta.fornecedor_id
                fornecedor_menor_nome = fornecedor.razao_social
                melhor_por_item[item_solic.id] = {
                    "fornecedor_id": proposta.fornecedor_id,
                    "fornecedor_nome": fornecedor.razao_social,
                    "proposta_id": proposta.id,
                    "item_proposta_id": item_proposta.id,
                    "preco_unitario": preco_final,
                    "preco_total": preco_total,
                    "produto_id": item_solic.produto_id,
                    "produto_nome": produto.nome if produto else "N/A",
                    "quantidade": quantidade
                }

        # Marcar menor preço e calcular diferenças
        for preco in precos_fornecedores:
            if preco.fornecedor_id == fornecedor_menor_id:
                preco.is_menor_preco = True
            if menor_preco_total and float(preco.preco_total) > 0:
                diff = ((float(preco.preco_total) - menor_preco_total) / menor_preco_total) * 100
                preco.diferenca_percentual = Decimal(str(round(diff, 2)))

        item_analise = AnaliseItemResponse(
            item_solicitacao_id=item_solic.id,
            produto_id=item_solic.produto_id,
            produto_nome=produto.nome if produto else "N/A",
            produto_codigo=produto.codigo if produto else None,
            quantidade=item_solic.quantidade,
            unidade_medida=item_solic.unidade_medida,
            precos_fornecedores=precos_fornecedores,
            menor_preco_unitario=Decimal(str(round(menor_preco_unitario, 2))) if menor_preco_unitario else None,
            menor_preco_total=Decimal(str(round(menor_preco_total, 2))) if menor_preco_total else None,
            fornecedor_menor_preco_id=fornecedor_menor_id,
            fornecedor_menor_preco_nome=fornecedor_menor_nome
        )
        itens_analise.append(item_analise)

    # Calcular resumo por fornecedor
    resumo_fornecedores = []
    for proposta in propostas:
        fornecedor = fornecedores_map.get(proposta.fornecedor_id)
        if not fornecedor:
            continue

        # Contar itens com menor preço deste fornecedor
        qtd_menor_preco = sum(
            1 for item_id, data in melhor_por_item.items()
            if data["fornecedor_id"] == proposta.fornecedor_id
        )

        resumo = ResumoFornecedor(
            fornecedor_id=proposta.fornecedor_id,
            fornecedor_nome=fornecedor.razao_social,
            proposta_id=proposta.id,
            valor_total=proposta.valor_total or Decimal(0),
            prazo_entrega=proposta.prazo_entrega,
            condicoes_pagamento=proposta.condicoes_pagamento,
            qtd_itens_cotados=len(proposta.itens),
            qtd_itens_menor_preco=qtd_menor_preco
        )
        resumo_fornecedores.append(resumo)

    # Ordenar por valor total
    resumo_fornecedores.sort(key=lambda x: float(x.valor_total or 0))

    # Menor valor global (compra única) - APENAS fornecedores que cotaram TODOS os itens
    if not resumo_fornecedores:
        raise HTTPException(status_code=400, detail="Nenhum fornecedor com proposta valida")

    total_itens_solicitacao = len(itens_solicitacao)
    fornecedores_completos = [
        f for f in resumo_fornecedores
        if f.qtd_itens_cotados == total_itens_solicitacao
    ]

    # Se há fornecedores que cotaram todos os itens, usar o menor deles
    # Caso contrário, não há opção válida de "compra única"
    if fornecedores_completos:
        menor_global = fornecedores_completos[0]
        menor_valor_global = float(menor_global.valor_total or 0)
        tem_opcao_compra_unica = True
    else:
        # Nenhum fornecedor cotou todos os itens - usar o primeiro apenas para referência
        menor_global = resumo_fornecedores[0]
        menor_valor_global = float(menor_global.valor_total or 0)
        tem_opcao_compra_unica = False

    # Calcular valor otimizado (melhor por item)
    valor_otimizado = sum(data["preco_total"] for data in melhor_por_item.values())

    # Economia
    economia = menor_valor_global - valor_otimizado
    economia_percentual = (economia / menor_valor_global * 100) if menor_valor_global > 0 else 0

    # Agrupar compra otimizada por fornecedor
    compra_por_fornecedor = {}
    for item_id, data in melhor_por_item.items():
        forn_id = data["fornecedor_id"]
        if forn_id not in compra_por_fornecedor:
            proposta = propostas_map.get(forn_id)
            compra_por_fornecedor[forn_id] = {
                "fornecedor_id": forn_id,
                "fornecedor_nome": data["fornecedor_nome"],
                "proposta_id": data["proposta_id"],
                "itens": [],
                "valor_total": 0,
                "prazo_entrega": proposta.prazo_entrega if proposta else None,
                "condicoes_pagamento": proposta.condicoes_pagamento if proposta else None
            }

        compra_por_fornecedor[forn_id]["itens"].append(ItemOtimizado(
            item_solicitacao_id=item_id,
            produto_id=data["produto_id"],
            produto_nome=data["produto_nome"],
            quantidade=Decimal(str(data["quantidade"])),
            fornecedor_id=forn_id,
            fornecedor_nome=data["fornecedor_nome"],
            proposta_id=data["proposta_id"],
            item_proposta_id=data["item_proposta_id"],
            preco_unitario=Decimal(str(round(data["preco_unitario"], 2))),
            preco_total=Decimal(str(round(data["preco_total"], 2)))
        ))
        compra_por_fornecedor[forn_id]["valor_total"] += data["preco_total"]

    compra_otimizada = [
        CompraOtimizadaPorFornecedor(
            fornecedor_id=data["fornecedor_id"],
            fornecedor_nome=data["fornecedor_nome"],
            proposta_id=data["proposta_id"],
            itens=data["itens"],
            valor_total=Decimal(str(round(data["valor_total"], 2))),
            prazo_entrega=data["prazo_entrega"],
            condicoes_pagamento=data["condicoes_pagamento"]
        )
        for data in compra_por_fornecedor.values()
    ]

    # Recomendação
    qtd_fornecedores_otimizado = len(compra_por_fornecedor)

    # Se nenhum fornecedor cotou todos os itens, sempre recomendar compra otimizada (split)
    if not tem_opcao_compra_unica:
        recomendacao = "COMPRA_OTIMIZADA"
        justificativa = f"Nenhum fornecedor cotou todos os {total_itens_solicitacao} itens. Necessário dividir entre {qtd_fornecedores_otimizado} fornecedor(es)."
    elif economia > 0 and economia_percentual >= 5 and qtd_fornecedores_otimizado <= 3:
        recomendacao = "COMPRA_OTIMIZADA"
        justificativa = f"Economia de R$ {economia:.2f} ({economia_percentual:.1f}%) ao dividir entre {qtd_fornecedores_otimizado} fornecedor(es)"
    elif economia > 0 and qtd_fornecedores_otimizado > 3:
        recomendacao = "COMPRA_UNICA"
        justificativa = f"Embora haja economia de R$ {economia:.2f}, seriam necessárias {qtd_fornecedores_otimizado} OCs. Recomendado compra única para simplificar."
    else:
        recomendacao = "COMPRA_UNICA"
        justificativa = f"Compra única de {menor_global.fornecedor_nome} tem melhor custo-benefício"

    return AnaliseOtimizadaResponse(
        solicitacao_id=solicitacao.id,
        solicitacao_numero=solicitacao.numero,
        solicitacao_titulo=solicitacao.titulo,
        itens=itens_analise,
        resumo_fornecedores=resumo_fornecedores,
        menor_valor_global=Decimal(str(round(menor_valor_global, 2))),
        fornecedor_menor_global_id=menor_global.fornecedor_id,
        fornecedor_menor_global_nome=menor_global.fornecedor_nome,
        valor_otimizado=Decimal(str(round(valor_otimizado, 2))),
        economia_otimizada=Decimal(str(round(economia, 2))),
        economia_percentual=Decimal(str(round(economia_percentual, 2))),
        compra_otimizada=compra_otimizada,
        recomendacao=recomendacao,
        justificativa=justificativa
    )


@router.post("/solicitacoes/{solicitacao_id}/gerar-ocs-otimizadas", response_model=GerarOCsOtimizadasResponse)
def gerar_ocs_otimizadas(
    solicitacao_id: int,
    request: GerarOCsOtimizadasRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Gerar múltiplas Ordens de Compra a partir de seleção otimizada.

    Permite escolher o melhor fornecedor para cada item,
    gerando automaticamente uma OC por fornecedor selecionado.
    """
    from app.models.pedido import PedidoCompra, ItemPedido, StatusPedido

    solicitacao = get_by_id(db, SolicitacaoCotacao, solicitacao_id, tenant_id, error_message="Solicitacao nao encontrada")

    # Validar que solicitação está em status válido
    if solicitacao.status == StatusSolicitacao.CANCELADA:
        raise HTTPException(status_code=400, detail="Solicitacao cancelada")

    if solicitacao.status == StatusSolicitacao.FINALIZADA:
        raise HTTPException(status_code=400, detail="Solicitacao ja finalizada. Ja existe OC gerada.")

    # Agrupar seleções por fornecedor
    selecoes_por_fornecedor = {}
    for selecao in request.selecoes:
        forn_id = selecao["fornecedor_id"]
        if forn_id not in selecoes_por_fornecedor:
            selecoes_por_fornecedor[forn_id] = []
        selecoes_por_fornecedor[forn_id].append(selecao)

    ocs_geradas = []
    valor_total_geral = Decimal(0)

    # Gerar uma OC por fornecedor
    for fornecedor_id, selecoes in selecoes_por_fornecedor.items():
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == fornecedor_id,
            Fornecedor.tenant_id == tenant_id
        ).first()

        if not fornecedor:
            raise HTTPException(status_code=400, detail=f"Fornecedor {fornecedor_id} nao encontrado")

        # Buscar proposta do fornecedor
        proposta = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id,
            PropostaFornecedor.fornecedor_id == fornecedor_id
        ).first()

        if not proposta:
            raise HTTPException(status_code=400, detail=f"Proposta do fornecedor {fornecedor.razao_social} nao encontrada")

        # Criar Pedido de Compra
        numero_pedido = generate_sequential_number(db, PedidoCompra, Prefixes.PEDIDO_COMPRA, tenant_id)

        pedido = PedidoCompra(
            numero=numero_pedido,
            solicitacao_cotacao_id=solicitacao.id,
            proposta_id=proposta.id,
            fornecedor_id=fornecedor_id,
            status=StatusPedido.RASCUNHO,
            data_pedido=datetime.utcnow(),
            condicoes_pagamento=proposta.condicoes_pagamento,
            prazo_entrega=proposta.prazo_entrega,
            frete_tipo=proposta.frete_tipo,
            observacoes=f"Gerado de análise otimizada - {request.justificativa}",
            tenant_id=tenant_id,
            created_by=current_user.id
        )
        db.add(pedido)
        db.flush()

        valor_pedido = Decimal(0)

        # Adicionar itens ao pedido
        for selecao in selecoes:
            item_proposta = db.query(ItemProposta).filter(
                ItemProposta.id == selecao["item_proposta_id"]
            ).first()

            if not item_proposta:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item de proposta {selecao['item_proposta_id']} nao encontrado"
                )

            item_solicitacao = db.query(ItemSolicitacao).filter(
                ItemSolicitacao.id == selecao["item_solicitacao_id"]
            ).first()

            if not item_solicitacao:
                continue

            produto = db.query(Produto).filter(Produto.id == item_solicitacao.produto_id).first()

            # Calcular valor
            preco_unitario = float(item_proposta.preco_unitario or 0)
            desconto = float(item_proposta.desconto_percentual or 0)
            preco_final = preco_unitario * (1 - desconto / 100)
            quantidade = float(item_solicitacao.quantidade)
            valor_item = Decimal(str(round(preco_final * quantidade, 2)))

            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                produto_id=item_solicitacao.produto_id,
                item_proposta_id=item_proposta.id,
                quantidade=item_solicitacao.quantidade,
                unidade_medida=item_solicitacao.unidade_medida,
                preco_unitario=Decimal(str(round(preco_final, 4))),
                desconto_percentual=Decimal(str(desconto)),
                valor_total=valor_item,
                especificacoes=item_solicitacao.especificacoes,
                marca=item_proposta.marca_oferecida,
                prazo_entrega_item=item_proposta.prazo_entrega_item,
                tenant_id=tenant_id
            )
            db.add(item_pedido)
            valor_pedido += valor_item

        # Atualizar totais do pedido
        pedido.valor_produtos = valor_pedido
        pedido.valor_frete = proposta.frete_valor or Decimal(0)
        pedido.valor_desconto = Decimal(0)
        pedido.valor_total = valor_pedido + (proposta.frete_valor or Decimal(0))

        valor_total_geral += pedido.valor_total

        ocs_geradas.append(OCGerada(
            pedido_id=pedido.id,
            pedido_numero=pedido.numero,
            fornecedor_id=fornecedor_id,
            fornecedor_nome=fornecedor.razao_social,
            valor_total=pedido.valor_total,
            qtd_itens=len(selecoes)
        ))

    # Atualizar status da solicitação
    solicitacao.status = StatusSolicitacao.FINALIZADA
    solicitacao.data_fechamento = datetime.utcnow()
    solicitacao.justificativa_escolha = f"Compra otimizada - {request.justificativa}"

    db.commit()

    # Calcular economia vs menor global
    propostas = db.query(PropostaFornecedor).filter(
        PropostaFornecedor.solicitacao_id == solicitacao_id,
        PropostaFornecedor.status.in_([StatusProposta.RECEBIDA, StatusProposta.VENCEDORA])
    ).all()

    menor_global = min(float(p.valor_total or 0) for p in propostas) if propostas else 0
    economia = Decimal(str(round(menor_global - float(valor_total_geral), 2))) if menor_global > 0 else None

    return GerarOCsOtimizadasResponse(
        solicitacao_id=solicitacao_id,
        ocs_geradas=ocs_geradas,
        valor_total=valor_total_geral,
        economia_vs_menor_global=economia
    )
