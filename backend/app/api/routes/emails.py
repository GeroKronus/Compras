"""
Rotas de Emails Processados - Sistema de Classificacao de Emails
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.api.deps import get_db, get_current_tenant_id, get_current_user
from app.models.email_processado import EmailProcessado, StatusEmailProcessado, MetodoClassificacao
from app.models.cotacao import SolicitacaoCotacao
from app.models.fornecedor import Fornecedor
from app.models.usuario import Usuario
from app.services.email_classifier import email_classifier
from app.services.email_service import email_service
from app.config import settings

router = APIRouter()


# ============ SCHEMAS ============

class EmailProcessadoResponse(BaseModel):
    id: int
    email_uid: str
    message_id: Optional[str]
    remetente: str
    remetente_nome: Optional[str]
    assunto: str
    data_recebimento: datetime
    corpo_resumo: Optional[str]
    status: StatusEmailProcessado
    metodo_classificacao: Optional[MetodoClassificacao]
    confianca_ia: Optional[int]
    motivo_classificacao: Optional[str]
    solicitacao_id: Optional[int]
    fornecedor_id: Optional[int]
    proposta_id: Optional[int]
    tenant_id: int
    processado_em: Optional[datetime]
    created_at: datetime
    # Campos enriquecidos
    solicitacao_numero: Optional[str] = None
    solicitacao_titulo: Optional[str] = None
    fornecedor_nome: Optional[str] = None

    class Config:
        from_attributes = True


class EmailProcessadoListResponse(BaseModel):
    items: List[EmailProcessadoResponse]
    total: int
    page: int
    page_size: int


class ClassificarManualmenteRequest(BaseModel):
    solicitacao_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    ignorar: bool = False


class ProcessarEmailsResponse(BaseModel):
    total_lidos: int
    novos: int
    classificados_assunto: int
    classificados_remetente: int
    classificados_ia: int
    pendentes_manual: int
    erros: int


# ============ ENDPOINTS DE CONFIG (devem vir antes de /{email_id}) ============

@router.get("/config/status")
def verificar_config_email():
    """
    Verificar se o servico de email e IA estao configurados.
    """
    import os
    chave_ia = os.environ.get('ANTHROPIC_API_KEY', '')

    return {
        "configurado": email_service.is_configured,
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "smtp_user_configurado": bool(settings.SMTP_USER),
        "smtp_password_configurado": bool(settings.SMTP_PASSWORD),
        "email_from": settings.EMAIL_FROM or "(usa SMTP_USER)",
        "ia_chave_configurada": bool(chave_ia),
        "ia_chave_inicio": chave_ia[:25] if chave_ia else "(vazio)",
        "ia_chave_fim": chave_ia[-15:] if chave_ia else "(vazio)",
        "ia_chave_tamanho": len(chave_ia)
    }


@router.get("/config/ia-status")
def verificar_config_ia():
    """
    Verificar se a IA (Anthropic) esta configurada.
    """
    import os

    # Pegar direto do ambiente para evitar problemas
    chave_env = os.environ.get('ANTHROPIC_API_KEY', '')
    chave_settings = getattr(settings, 'ANTHROPIC_API_KEY', '') or ''

    return {
        "anthropic_configurado_env": bool(chave_env),
        "anthropic_configurado_settings": bool(chave_settings),
        "chave_env_inicio": chave_env[:20] + "..." if len(chave_env) > 20 else chave_env if chave_env else "(vazio)",
        "chave_env_fim": "..." + chave_env[-10:] if len(chave_env) > 10 else chave_env if chave_env else "(vazio)",
        "chave_env_tamanho": len(chave_env),
        "chave_settings_inicio": chave_settings[:20] + "..." if len(chave_settings) > 20 else chave_settings if chave_settings else "(vazio)",
        "chave_settings_tamanho": len(chave_settings)
    }


@router.get("/config/ia-testar")
def testar_conexao_ia():
    """
    Testa a conexao com a API da Anthropic.
    """
    from app.services.ai_service import ai_service

    if not ai_service.is_available:
        return {"teste": "FALHOU", "erro": "ai_service nao disponivel"}

    try:
        response = ai_service.client.messages.create(
            model=ai_service.MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "Diga apenas: OK"}]
        )
        return {
            "teste": "OK",
            "resposta": response.content[0].text
        }
    except Exception as e:
        return {"teste": "FALHOU", "erro": str(e)}


# ============ ENDPOINTS ============

@router.post("/processar", response_model=ProcessarEmailsResponse)
def processar_emails_novos(
    dias_atras: int = Query(7, ge=1, le=30, description="Quantos dias atras buscar emails"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Processa emails novos da caixa de entrada.

    1. Le emails dos ultimos N dias
    2. Classifica automaticamente usando estrategia em camadas:
       - ASSUNTO: Busca padrao "COTACAO #XXX"
       - REMETENTE: Associa pelo email do fornecedor
       - IA: Analise de conteudo para emails orfaos
    3. Emails nao classificados ficam PENDENTES para revisao manual
    """
    resultado = email_classifier.processar_emails_novos(db, tenant_id, dias_atras)

    if "error" in resultado:
        raise HTTPException(status_code=503, detail=resultado["error"])

    return resultado


@router.get("/", response_model=EmailProcessadoListResponse)
def listar_emails_processados(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[StatusEmailProcessado] = None,
    metodo: Optional[MetodoClassificacao] = None,
    solicitacao_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    busca: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Listar emails processados com filtros.

    Filtros disponiveis:
    - status: pendente, classificado, ignorado, erro
    - metodo: assunto, remetente, ia, manual
    - solicitacao_id: ID da solicitacao relacionada
    - fornecedor_id: ID do fornecedor
    - busca: texto no assunto ou remetente
    """
    query = db.query(EmailProcessado).filter(EmailProcessado.tenant_id == tenant_id)

    if status:
        query = query.filter(EmailProcessado.status == status)
    if metodo:
        query = query.filter(EmailProcessado.metodo_classificacao == metodo)
    if solicitacao_id:
        query = query.filter(EmailProcessado.solicitacao_id == solicitacao_id)
    if fornecedor_id:
        query = query.filter(EmailProcessado.fornecedor_id == fornecedor_id)
    if busca:
        query = query.filter(
            (EmailProcessado.assunto.ilike(f"%{busca}%")) |
            (EmailProcessado.remetente.ilike(f"%{busca}%"))
        )

    # Contar total
    total = query.count()

    # Paginar
    query = query.order_by(desc(EmailProcessado.data_recebimento))
    query = query.offset((page - 1) * page_size).limit(page_size)

    emails = query.all()
    items = [_enrich_email_response(e, db) for e in emails]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/pendentes", response_model=EmailProcessadoListResponse)
def listar_emails_pendentes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Listar emails pendentes de classificacao manual.

    Retorna apenas emails com status PENDENTE que precisam
    de revisao humana para serem classificados.
    """
    query = db.query(EmailProcessado).filter(
        EmailProcessado.tenant_id == tenant_id,
        EmailProcessado.status == StatusEmailProcessado.PENDENTE
    )

    total = query.count()
    query = query.order_by(desc(EmailProcessado.data_recebimento))
    query = query.offset((page - 1) * page_size).limit(page_size)

    emails = query.all()
    items = [_enrich_email_response(e, db) for e in emails]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{email_id}", response_model=EmailProcessadoResponse)
def obter_email(
    email_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter detalhes de um email processado"""
    email = db.query(EmailProcessado).filter(
        EmailProcessado.id == email_id,
        EmailProcessado.tenant_id == tenant_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email nao encontrado")

    return _enrich_email_response(email, db, incluir_corpo_completo=True)


@router.get("/{email_id}/corpo")
def obter_corpo_email(
    email_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter corpo completo de um email processado"""
    email = db.query(EmailProcessado).filter(
        EmailProcessado.id == email_id,
        EmailProcessado.tenant_id == tenant_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email nao encontrado")

    return {
        "id": email.id,
        "assunto": email.assunto,
        "remetente": email.remetente,
        "corpo_completo": email.corpo_completo
    }


@router.post("/{email_id}/classificar")
def classificar_email_manualmente(
    email_id: int,
    dados: ClassificarManualmenteRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Classificar email manualmente.

    - Se ignorar=True: marca o email para ser ignorado
    - Se solicitacao_id: associa a uma solicitacao de cotacao
    - Se fornecedor_id: associa a um fornecedor
    """
    # Validar se email existe
    email = db.query(EmailProcessado).filter(
        EmailProcessado.id == email_id,
        EmailProcessado.tenant_id == tenant_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email nao encontrado")

    # Validar solicitacao se informada
    if dados.solicitacao_id:
        solicitacao = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.id == dados.solicitacao_id,
            SolicitacaoCotacao.tenant_id == tenant_id
        ).first()
        if not solicitacao:
            raise HTTPException(status_code=404, detail="Solicitacao nao encontrada")

    # Validar fornecedor se informado
    if dados.fornecedor_id:
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == dados.fornecedor_id,
            Fornecedor.tenant_id == tenant_id
        ).first()
        if not fornecedor:
            raise HTTPException(status_code=404, detail="Fornecedor nao encontrado")

    sucesso = email_classifier.classificar_manualmente(
        db,
        email_id,
        dados.solicitacao_id,
        dados.fornecedor_id,
        dados.ignorar
    )

    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao classificar email")

    return {
        "sucesso": True,
        "email_id": email_id,
        "status": "ignorado" if dados.ignorar else "classificado",
        "solicitacao_id": dados.solicitacao_id,
        "fornecedor_id": dados.fornecedor_id
    }


@router.post("/{email_id}/criar-proposta")
def criar_proposta_de_email(
    email_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Criar proposta de fornecedor a partir de um email classificado.

    O email deve estar CLASSIFICADO e ter solicitacao_id e fornecedor_id definidos.
    Os dados extraidos pelo IA serao usados para preencher a proposta.
    """
    email = db.query(EmailProcessado).filter(
        EmailProcessado.id == email_id,
        EmailProcessado.tenant_id == tenant_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email nao encontrado")

    if email.status != StatusEmailProcessado.CLASSIFICADO:
        raise HTTPException(status_code=400, detail="Email deve estar classificado para criar proposta")

    if not email.solicitacao_id or not email.fornecedor_id:
        raise HTTPException(status_code=400, detail="Email deve ter solicitacao e fornecedor definidos")

    proposta_id = email_classifier.criar_proposta_de_email(db, email_id)

    if not proposta_id:
        raise HTTPException(status_code=500, detail="Erro ao criar proposta")

    return {
        "sucesso": True,
        "email_id": email_id,
        "proposta_id": proposta_id
    }


@router.get("/estatisticas/resumo")
def obter_estatisticas_emails(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Obter estatisticas dos emails processados.

    Retorna contagem por status e metodo de classificacao.
    """
    from sqlalchemy import func

    # Total por status
    status_counts = db.query(
        EmailProcessado.status,
        func.count(EmailProcessado.id)
    ).filter(
        EmailProcessado.tenant_id == tenant_id
    ).group_by(
        EmailProcessado.status
    ).all()

    # Total por metodo
    metodo_counts = db.query(
        EmailProcessado.metodo_classificacao,
        func.count(EmailProcessado.id)
    ).filter(
        EmailProcessado.tenant_id == tenant_id,
        EmailProcessado.metodo_classificacao.isnot(None)
    ).group_by(
        EmailProcessado.metodo_classificacao
    ).all()

    return {
        "total": sum(c[1] for c in status_counts),
        "por_status": {
            s.value if s else "null": c for s, c in status_counts
        },
        "por_metodo": {
            m.value if m else "null": c for m, c in metodo_counts
        }
    }


# ============ CONTROLE DO JOB AUTOMATICO ============

@router.post("/job/iniciar")
def iniciar_job_emails(
    intervalo_minutos: int = Query(5, ge=1, le=60, description="Intervalo em minutos"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Iniciar verificacao automatica de emails.

    O job ira processar emails novos a cada X minutos para todos os tenants.
    Requer usuario autenticado (admin).
    """
    from app.jobs.email_job import iniciar_scheduler, status_scheduler

    iniciar_scheduler(intervalo_minutos)
    return {
        "sucesso": True,
        "mensagem": f"Job de emails iniciado - verificando a cada {intervalo_minutos} minutos",
        "status": status_scheduler()
    }


@router.post("/job/parar")
def parar_job_emails(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Parar verificacao automatica de emails.
    """
    from app.jobs.email_job import parar_scheduler

    parar_scheduler()
    return {
        "sucesso": True,
        "mensagem": "Job de emails parado"
    }


@router.post("/job/executar-agora")
def executar_job_agora(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Executar processamento de emails imediatamente (sem aguardar scheduler).

    Processa emails apenas para o tenant atual.
    """
    resultado = email_classifier.processar_emails_novos(db, tenant_id, dias_atras=7)

    if "error" in resultado:
        raise HTTPException(status_code=503, detail=resultado["error"])

    return {
        "sucesso": True,
        "mensagem": "Processamento executado",
        "resultado": resultado
    }


@router.get("/job/status")
def status_job_emails(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter status do job de verificacao automatica.
    """
    from app.jobs.email_job import status_scheduler

    return status_scheduler()


# ============ TESTE DE EMAIL ============

class TesteEmailRequest(BaseModel):
    destinatario: str
    assunto: Optional[str] = "Teste de Email - Sistema de Compras"
    mensagem: Optional[str] = "Este e um email de teste do Sistema de Gestao de Compras."


@router.get("/teste/{email_destino}")
def enviar_email_teste_publico(
    email_destino: str
):
    """
    Enviar email de teste (publico, sem autenticacao).
    Exemplo: /api/v1/emails/teste/seu@email.com
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime

    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Email nao configurado. Configure SMTP_USER e SMTP_PASSWORD no Railway."
        )

    debug_info = {
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "user": settings.SMTP_USER,
        "email_from": settings.EMAIL_FROM or settings.SMTP_USER,
        "destino": email_destino,
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Teste direto de conexao SMTP
        msg = MIMEMultipart('alternative')
        remetente = settings.EMAIL_FROM or settings.SMTP_USER
        msg['From'] = remetente
        msg['To'] = email_destino
        msg['Subject'] = f"Teste - Sistema de Compras - {datetime.now().strftime('%H:%M:%S')}"

        corpo = f"""
        <html>
        <body>
            <h1>Email funcionando!</h1>
            <p>Teste OK - {datetime.now().isoformat()}</p>
            <p>De: {remetente}</p>
            <p>Para: {email_destino}</p>
            <p>Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(corpo, 'html', 'utf-8'))

        # Conectar SSL
        debug_info["etapa"] = "conectando"
        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30)

        debug_info["etapa"] = "login"
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        debug_info["etapa"] = "enviando"
        result = server.sendmail(settings.SMTP_USER, email_destino, msg.as_string())
        debug_info["sendmail_result"] = str(result) if result else "OK (vazio = sucesso)"

        debug_info["etapa"] = "quit"
        server.quit()

        return {
            "sucesso": True,
            "para": email_destino,
            "de": remetente,
            "debug": debug_info
        }

    except smtplib.SMTPAuthenticationError as e:
        debug_info["erro_tipo"] = "SMTPAuthenticationError"
        debug_info["smtp_code"] = e.smtp_code
        debug_info["smtp_error"] = str(e.smtp_error)
        raise HTTPException(status_code=401, detail={"msg": "Erro autenticacao", "debug": debug_info})
    except smtplib.SMTPRecipientsRefused as e:
        debug_info["erro_tipo"] = "SMTPRecipientsRefused"
        debug_info["recipients"] = str(e.recipients)
        raise HTTPException(status_code=400, detail={"msg": "Destinatario recusado", "debug": debug_info})
    except smtplib.SMTPException as e:
        debug_info["erro_tipo"] = type(e).__name__
        debug_info["erro_msg"] = str(e)
        raise HTTPException(status_code=500, detail={"msg": "Erro SMTP", "debug": debug_info})
    except Exception as e:
        debug_info["erro_tipo"] = type(e).__name__
        debug_info["erro_msg"] = str(e)
        raise HTTPException(status_code=500, detail={"msg": "Erro geral", "debug": debug_info})


@router.post("/teste/enviar")
def enviar_email_teste(
    dados: TesteEmailRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Enviar email de teste para verificar configuracao SMTP.

    Apenas usuarios autenticados podem usar este endpoint.
    Envia um email simples para o destinatario informado.
    """
    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Servico de email nao configurado",
                "smtp_user_configurado": bool(settings.SMTP_USER),
                "smtp_password_configurado": bool(settings.SMTP_PASSWORD)
            }
        )

    corpo_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .success {{ background: #10b981; color: white; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Sistema de Compras</h1>
            <p style="margin: 10px 0 0 0;">Teste de Email</p>
        </div>
        <div class="content">
            <div class="success">
                ✅ Email enviado com sucesso!
            </div>
            <p><strong>Mensagem:</strong></p>
            <p>{dados.mensagem}</p>
            <p><strong>Enviado por:</strong> {current_user.nome_completo} ({current_user.email})</p>
        </div>
        <div class="footer">
            <p>Este e um email de teste do Sistema de Gestao de Compras</p>
            <p>Se voce recebeu este email, a configuracao SMTP esta funcionando corretamente.</p>
        </div>
    </div>
</body>
</html>
"""

    sucesso = email_service.enviar_email(
        destinatario=dados.destinatario,
        assunto=dados.assunto,
        corpo_html=corpo_html,
        corpo_texto=f"{dados.assunto}\n\n{dados.mensagem}\n\nEnviado por: {current_user.nome_completo}"
    )

    if sucesso:
        return {
            "sucesso": True,
            "mensagem": f"Email de teste enviado para {dados.destinatario}",
            "de": settings.EMAIL_FROM or settings.SMTP_USER,
            "para": dados.destinatario,
            "assunto": dados.assunto
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Falha ao enviar email. Verifique as credenciais SMTP."
        )


# ============ REPROCESSAMENTO COM IA ============

class ReprocessarExtracaoResponse(BaseModel):
    total_reprocessados: int
    total_com_dados: int
    total_erros: int
    detalhes: List[dict]


@router.post("/reprocessar-extracao", response_model=ReprocessarExtracaoResponse)
def reprocessar_extracao_emails(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Reprocessa emails classificados para extrair dados via IA.

    Busca emails que:
    - Estao com status CLASSIFICADO
    - Tem proposta_id definido
    - NAO tem dados_extraidos ou dados_extraidos esta vazio

    Para cada email, usa a IA para extrair dados comerciais (preco, prazo, etc)
    e atualiza a proposta correspondente.
    """
    from app.services.ai_service import ai_service
    from app.models.cotacao import PropostaFornecedor, StatusProposta, ItemSolicitacao, ItemProposta
    import json

    if not ai_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="Servico de IA nao configurado. Configure ANTHROPIC_API_KEY."
        )

    # Buscar emails classificados sem dados extraidos
    emails = db.query(EmailProcessado).filter(
        EmailProcessado.tenant_id == tenant_id,
        EmailProcessado.status == StatusEmailProcessado.CLASSIFICADO,
        EmailProcessado.proposta_id.isnot(None),
        (EmailProcessado.dados_extraidos.is_(None)) | (EmailProcessado.dados_extraidos == '') | (EmailProcessado.dados_extraidos == '{}')
    ).all()

    resultado = {
        "total_reprocessados": 0,
        "total_com_dados": 0,
        "total_erros": 0,
        "detalhes": []
    }

    for email in emails:
        resultado["total_reprocessados"] += 1
        detalhe = {
            "email_id": email.id,
            "assunto": email.assunto,
            "proposta_id": email.proposta_id,
            "sucesso": False,
            "erro": None,
            "dados_extraidos": None
        }

        try:
            # Verificar se tem corpo
            if not email.corpo_completo:
                detalhe["erro"] = "Email sem corpo"
                resultado["total_erros"] += 1
                resultado["detalhes"].append(detalhe)
                continue

            # Extrair dados via IA
            dados = ai_service.extrair_dados_proposta_email(email.corpo_completo)

            if "error" in dados:
                detalhe["erro"] = dados["error"]
                resultado["total_erros"] += 1
                resultado["detalhes"].append(detalhe)
                continue

            # Atualizar email com dados extraidos
            email.dados_extraidos = json.dumps(dados)
            detalhe["dados_extraidos"] = dados

            # Atualizar proposta com dados
            proposta = db.query(PropostaFornecedor).filter(
                PropostaFornecedor.id == email.proposta_id
            ).first()

            if proposta:
                # Atualizar campos da proposta
                if dados.get('prazo_entrega_dias') is not None:
                    proposta.prazo_entrega = dados['prazo_entrega_dias']

                if dados.get('condicoes_pagamento'):
                    proposta.condicoes_pagamento = dados['condicoes_pagamento']

                if dados.get('observacoes'):
                    proposta.observacoes = dados['observacoes']

                if dados.get('frete_incluso') is not None:
                    proposta.frete_tipo = 'CIF' if dados['frete_incluso'] else 'FOB'

                if dados.get('frete_valor') is not None:
                    proposta.frete_valor = dados['frete_valor']

                # Calcular valor total
                preco_total = dados.get('preco_total')
                preco_unitario = dados.get('preco_unitario')

                if preco_total:
                    proposta.valor_total = preco_total
                elif preco_unitario and dados.get('quantidade'):
                    proposta.valor_total = preco_unitario * dados['quantidade']

                # Criar/atualizar ItemProposta se tiver preco unitario
                if preco_unitario:
                    item_solicitacao = db.query(ItemSolicitacao).filter(
                        ItemSolicitacao.solicitacao_id == proposta.solicitacao_id
                    ).first()

                    if item_solicitacao:
                        item_proposta = db.query(ItemProposta).filter(
                            ItemProposta.proposta_id == proposta.id,
                            ItemProposta.item_solicitacao_id == item_solicitacao.id
                        ).first()

                        if item_proposta:
                            item_proposta.preco_unitario = preco_unitario
                            item_proposta.preco_final = preco_unitario
                            if dados.get('marca_produto'):
                                item_proposta.marca_oferecida = dados['marca_produto']
                        else:
                            item_proposta = ItemProposta(
                                proposta_id=proposta.id,
                                item_solicitacao_id=item_solicitacao.id,
                                preco_unitario=preco_unitario,
                                preco_final=preco_unitario,
                                quantidade_disponivel=dados.get('quantidade'),
                                marca_oferecida=dados.get('marca_produto'),
                                tenant_id=tenant_id
                            )
                            db.add(item_proposta)

            db.commit()
            detalhe["sucesso"] = True
            resultado["total_com_dados"] += 1

        except Exception as e:
            detalhe["erro"] = str(e)
            resultado["total_erros"] += 1
            db.rollback()

        resultado["detalhes"].append(detalhe)

    return resultado


@router.post("/{email_id}/extrair-dados")
def extrair_dados_email(
    email_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Extrai dados comerciais de um email especifico usando IA.

    Util para reprocessar um email individual e extrair
    precos, prazos, condicoes de pagamento, etc.
    """
    from app.services.ai_service import ai_service
    from app.models.cotacao import PropostaFornecedor, ItemSolicitacao, ItemProposta
    import json

    if not ai_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="Servico de IA nao configurado. Configure ANTHROPIC_API_KEY."
        )

    # Buscar email
    email = db.query(EmailProcessado).filter(
        EmailProcessado.id == email_id,
        EmailProcessado.tenant_id == tenant_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email nao encontrado")

    if not email.corpo_completo:
        raise HTTPException(status_code=400, detail="Email sem corpo para extrair dados")

    # Extrair dados via IA
    dados = ai_service.extrair_dados_proposta_email(email.corpo_completo)

    if "error" in dados:
        raise HTTPException(status_code=500, detail=dados["error"])

    # Atualizar email com dados extraidos
    email.dados_extraidos = json.dumps(dados)

    # Se tiver proposta_id, atualizar proposta
    if email.proposta_id:
        proposta = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.id == email.proposta_id
        ).first()

        if proposta:
            if dados.get('prazo_entrega_dias') is not None:
                proposta.prazo_entrega = dados['prazo_entrega_dias']

            if dados.get('condicoes_pagamento'):
                proposta.condicoes_pagamento = dados['condicoes_pagamento']

            if dados.get('observacoes'):
                proposta.observacoes = dados['observacoes']

            if dados.get('frete_incluso') is not None:
                proposta.frete_tipo = 'CIF' if dados['frete_incluso'] else 'FOB'

            if dados.get('frete_valor') is not None:
                proposta.frete_valor = dados['frete_valor']

            preco_total = dados.get('preco_total')
            preco_unitario = dados.get('preco_unitario')

            if preco_total:
                proposta.valor_total = preco_total
            elif preco_unitario and dados.get('quantidade'):
                proposta.valor_total = preco_unitario * dados['quantidade']

            if preco_unitario:
                item_solicitacao = db.query(ItemSolicitacao).filter(
                    ItemSolicitacao.solicitacao_id == proposta.solicitacao_id
                ).first()

                if item_solicitacao:
                    item_proposta = db.query(ItemProposta).filter(
                        ItemProposta.proposta_id == proposta.id,
                        ItemProposta.item_solicitacao_id == item_solicitacao.id
                    ).first()

                    if item_proposta:
                        item_proposta.preco_unitario = preco_unitario
                        item_proposta.preco_final = preco_unitario
                        if dados.get('marca_produto'):
                            item_proposta.marca_oferecida = dados['marca_produto']
                    else:
                        item_proposta = ItemProposta(
                            proposta_id=proposta.id,
                            item_solicitacao_id=item_solicitacao.id,
                            preco_unitario=preco_unitario,
                            preco_final=preco_unitario,
                            quantidade_disponivel=dados.get('quantidade'),
                            marca_oferecida=dados.get('marca_produto'),
                            tenant_id=tenant_id
                        )
                        db.add(item_proposta)

    db.commit()

    return {
        "sucesso": True,
        "email_id": email_id,
        "proposta_id": email.proposta_id,
        "dados_extraidos": dados,
        "confianca": dados.get('confianca_extracao', 0)
    }


# ============ HELPERS ============

def _enrich_email_response(email: EmailProcessado, db: Session, incluir_corpo_completo: bool = False) -> dict:
    """Enriquecer resposta com dados relacionados"""
    response = {
        "id": email.id,
        "email_uid": email.email_uid,
        "message_id": email.message_id,
        "remetente": email.remetente,
        "remetente_nome": email.remetente_nome,
        "assunto": email.assunto,
        "data_recebimento": email.data_recebimento,
        "corpo_resumo": email.corpo_resumo,
        "status": email.status,
        "metodo_classificacao": email.metodo_classificacao,
        "confianca_ia": email.confianca_ia,
        "motivo_classificacao": email.motivo_classificacao,
        "solicitacao_id": email.solicitacao_id,
        "fornecedor_id": email.fornecedor_id,
        "proposta_id": email.proposta_id,
        "tenant_id": email.tenant_id,
        "processado_em": email.processado_em,
        "created_at": email.created_at,
        "solicitacao_numero": None,
        "solicitacao_titulo": None,
        "fornecedor_nome": None
    }

    # Adicionar corpo completo se solicitado
    if incluir_corpo_completo:
        response["corpo_completo"] = email.corpo_completo

    # Enriquecer com dados da solicitacao
    if email.solicitacao_id:
        solicitacao = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.id == email.solicitacao_id
        ).first()
        if solicitacao:
            response["solicitacao_numero"] = solicitacao.numero
            response["solicitacao_titulo"] = solicitacao.titulo

    # Enriquecer com dados do fornecedor
    if email.fornecedor_id:
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == email.fornecedor_id
        ).first()
        if fornecedor:
            response["fornecedor_nome"] = fornecedor.razao_social

    return response
