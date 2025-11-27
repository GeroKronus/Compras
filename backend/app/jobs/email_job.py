"""
Job para verificacao automatica de emails
Executa periodicamente para processar novos emails da caixa de entrada
So processa se houver solicitacoes de cotacao pendentes
"""
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.cotacao import SolicitacaoCotacao, StatusSolicitacao
from app.services.email_classifier import email_classifier
from app.services.email_service import email_service

# Scheduler global
scheduler: Optional[BackgroundScheduler] = None


def verificar_solicitacoes_pendentes(db: Session, tenant_id: int) -> int:
    """
    Verifica quantas solicitacoes de cotacao estao pendentes de resposta.

    Uma solicitacao esta pendente se:
    - Status = ENVIADA (enviada para fornecedores, aguardando resposta)
    - Status = EM_COTACAO (ja recebeu algumas respostas, mas ainda aguardando mais)

    Args:
        db: Sessao do banco
        tenant_id: ID do tenant

    Returns:
        Numero de solicitacoes pendentes
    """
    return db.query(SolicitacaoCotacao).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status.in_([
            StatusSolicitacao.ENVIADA,
            StatusSolicitacao.EM_COTACAO
        ])
    ).count()


def processar_emails_todos_tenants():
    """
    Processa emails para todos os tenants ativos.

    IMPORTANTE: So processa emails de tenants que possuem
    solicitacoes de cotacao pendentes (ENVIADA ou EM_COTACAO).
    Isso evita processamento desnecessario e economiza recursos.

    Esta funcao e executada pelo scheduler a cada X minutos.
    """
    if not email_service.is_configured:
        print("[EMAIL JOB] Servico de email nao configurado. Pulando processamento.")
        return

    print(f"[EMAIL JOB] Iniciando processamento de emails - {datetime.now()}")

    db: Session = SessionLocal()
    try:
        # Buscar todos os tenants ativos
        tenants = db.query(Tenant).filter(Tenant.ativo == True).all()

        total_processados = 0
        total_novos = 0
        tenants_pulados = 0

        for tenant in tenants:
            try:
                # Verificar se ha solicitacoes pendentes
                solicitacoes_pendentes = verificar_solicitacoes_pendentes(db, tenant.id)

                if solicitacoes_pendentes == 0:
                    # Nao ha solicitacoes pendentes, pular este tenant
                    tenants_pulados += 1
                    continue

                print(f"[EMAIL JOB] Tenant {tenant.id} ({tenant.nome_empresa}): "
                      f"{solicitacoes_pendentes} solicitacoes pendentes, verificando emails...")

                resultado = email_classifier.processar_emails_novos(
                    db=db,
                    tenant_id=tenant.id,
                    dias_atras=3  # Verificar ultimos 3 dias
                )

                if "error" not in resultado:
                    total_processados += resultado.get("total_lidos", 0)
                    total_novos += resultado.get("novos", 0)

                    if resultado.get("novos", 0) > 0:
                        print(f"[EMAIL JOB] Tenant {tenant.id} ({tenant.nome_empresa}): "
                              f"{resultado['novos']} novos emails processados - "
                              f"Assunto: {resultado['classificados_assunto']}, "
                              f"Remetente: {resultado['classificados_remetente']}, "
                              f"IA: {resultado['classificados_ia']}, "
                              f"Pendentes: {resultado['pendentes_manual']}")
                else:
                    print(f"[EMAIL JOB] Erro no tenant {tenant.id}: {resultado['error']}")

            except Exception as e:
                print(f"[EMAIL JOB] Erro ao processar tenant {tenant.id}: {e}")
                continue

        print(f"[EMAIL JOB] Processamento concluido - "
              f"Total lidos: {total_processados}, Novos: {total_novos}, "
              f"Tenants pulados (sem solicitacoes): {tenants_pulados}")

    except Exception as e:
        print(f"[EMAIL JOB] Erro geral no processamento: {e}")

    finally:
        db.close()


def iniciar_scheduler(intervalo_minutos: int = 5):
    """
    Inicia o scheduler para verificacao periodica de emails.

    Args:
        intervalo_minutos: Intervalo entre execucoes (padrao: 5 minutos)
    """
    global scheduler

    if scheduler is not None:
        print("[EMAIL JOB] Scheduler ja iniciado")
        return

    scheduler = BackgroundScheduler()

    # Adicionar job de emails
    scheduler.add_job(
        func=processar_emails_todos_tenants,
        trigger=IntervalTrigger(minutes=intervalo_minutos),
        id='email_processor',
        name='Processador de emails de cotacao',
        replace_existing=True
    )

    scheduler.start()
    print(f"[EMAIL JOB] Scheduler iniciado - verificando emails a cada {intervalo_minutos} minutos")


def parar_scheduler():
    """Para o scheduler"""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        print("[EMAIL JOB] Scheduler parado")


def executar_agora():
    """Executa o processamento de emails imediatamente (sem aguardar scheduler)"""
    processar_emails_todos_tenants()


def status_scheduler() -> dict:
    """Retorna status do scheduler"""
    global scheduler

    if scheduler is None:
        return {
            "ativo": False,
            "mensagem": "Scheduler nao iniciado"
        }

    jobs = scheduler.get_jobs()
    return {
        "ativo": True,
        "jobs": [
            {
                "id": job.id,
                "nome": job.name,
                "proxima_execucao": str(job.next_run_time) if job.next_run_time else None
            }
            for job in jobs
        ]
    }
