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


@router.get("/config/status")
def verificar_config_email(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Verificar se o servico de email esta configurado.
    Retorna status das variaveis de ambiente necessarias.
    """
    return {
        "configurado": email_service.is_configured,
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "smtp_user_configurado": bool(settings.SMTP_USER),
        "smtp_password_configurado": bool(settings.SMTP_PASSWORD),
        "email_from": settings.EMAIL_FROM or "(usa SMTP_USER)",
        "imap_host": settings.IMAP_HOST,
        "imap_port": settings.IMAP_PORT
    }


@router.get("/teste/enviar/{email_destino}")
def enviar_email_teste_get(
    email_destino: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Enviar email de teste via GET (para teste rapido no navegador).

    Exemplo: /api/v1/emails/teste/enviar/seu@email.com
    """
    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Servico de email nao configurado. Configure SMTP_USER e SMTP_PASSWORD."
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
            <p>Este e um email de teste do Sistema de Gestao de Compras.</p>
            <p><strong>Enviado por:</strong> {current_user.nome_completo} ({current_user.email})</p>
        </div>
        <div class="footer">
            <p>Se voce recebeu este email, a configuracao SMTP esta funcionando corretamente.</p>
        </div>
    </div>
</body>
</html>
"""

    sucesso = email_service.enviar_email(
        destinatario=email_destino,
        assunto="Teste de Email - Sistema de Compras",
        corpo_html=corpo_html,
        corpo_texto=f"Teste de Email - Sistema de Compras\n\nEnviado por: {current_user.nome_completo}"
    )

    if sucesso:
        return {
            "sucesso": True,
            "mensagem": f"Email de teste enviado para {email_destino}",
            "de": settings.EMAIL_FROM or settings.SMTP_USER,
            "para": email_destino
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Falha ao enviar email. Verifique as credenciais SMTP."
        )


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
