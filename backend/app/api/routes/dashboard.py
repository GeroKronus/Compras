"""
Rotas do Dashboard - Alertas e Estatisticas em tempo real
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.api.deps import get_db, get_current_tenant_id, get_current_user
from app.models.cotacao import (
    SolicitacaoCotacao, PropostaFornecedor,
    StatusSolicitacao, StatusProposta
)
from app.models.email_processado import EmailProcessado
from app.models.fornecedor import Fornecedor
from app.models.produto import Produto
from app.models.usuario import Usuario

router = APIRouter()


# ============ SCHEMAS ============

class AlertaResponse(BaseModel):
    tipo: str  # 'propostas_recebidas', 'emails_pendentes', 'cotacao_vencendo', etc.
    prioridade: str  # 'alta', 'media', 'baixa'
    titulo: str
    mensagem: str
    link: Optional[str] = None
    dados: Optional[dict] = None
    created_at: datetime


class SolicitacaoComRespostasResponse(BaseModel):
    id: int
    numero: str
    titulo: str
    status: str
    total_fornecedores: int
    propostas_recebidas: int
    propostas_pendentes: int
    melhor_proposta: Optional[dict] = None
    data_limite: Optional[datetime] = None
    created_at: datetime


class DashboardStatsResponse(BaseModel):
    cotacoes_pendentes: int
    cotacoes_em_andamento: int
    cotacoes_finalizadas: int
    emails_pendentes: int
    emails_classificados: int
    fornecedores_ativos: int
    produtos_cadastrados: int
    total_compras_mes: float


class AlertasResumoResponse(BaseModel):
    alertas: List[AlertaResponse]
    solicitacoes_com_respostas: List[SolicitacaoComRespostasResponse]
    stats: DashboardStatsResponse


# ============ ENDPOINTS ============

@router.get("/alertas", response_model=AlertasResumoResponse)
def obter_alertas_dashboard(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter todos os alertas e notificacoes para o dashboard.

    Retorna:
    - Alertas de acoes pendentes
    - Solicitacoes que receberam propostas
    - Estatisticas gerais
    """
    alertas = []
    now = datetime.utcnow()

    # 1. Buscar solicitacoes em cotacao que receberam propostas
    solicitacoes_em_cotacao = db.query(SolicitacaoCotacao).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status.in_([StatusSolicitacao.ENVIADA, StatusSolicitacao.EM_COTACAO])
    ).all()

    solicitacoes_com_respostas = []

    for sol in solicitacoes_em_cotacao:
        # Contar propostas
        propostas = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == sol.id,
            PropostaFornecedor.tenant_id == tenant_id
        ).all()

        total_fornecedores = len(propostas)
        propostas_recebidas = sum(1 for p in propostas if p.status == StatusProposta.RECEBIDA)
        propostas_pendentes = sum(1 for p in propostas if p.status == StatusProposta.PENDENTE)

        # Encontrar melhor proposta (menor valor total)
        melhor_proposta = None
        propostas_com_valor = [p for p in propostas if p.status == StatusProposta.RECEBIDA and p.valor_total]
        if propostas_com_valor:
            melhor = min(propostas_com_valor, key=lambda p: p.valor_total or float('inf'))
            fornecedor = db.query(Fornecedor).filter(Fornecedor.id == melhor.fornecedor_id).first()
            melhor_proposta = {
                "fornecedor_id": melhor.fornecedor_id,
                "fornecedor_nome": fornecedor.razao_social if fornecedor else "N/A",
                "valor_total": float(melhor.valor_total) if melhor.valor_total else 0,
                "prazo_entrega": melhor.prazo_entrega,
                "condicoes_pagamento": melhor.condicoes_pagamento
            }

        # Se tem propostas recebidas, adicionar na lista
        if propostas_recebidas > 0:
            solicitacoes_com_respostas.append(SolicitacaoComRespostasResponse(
                id=sol.id,
                numero=sol.numero,
                titulo=sol.titulo,
                status=sol.status.value,
                total_fornecedores=total_fornecedores,
                propostas_recebidas=propostas_recebidas,
                propostas_pendentes=propostas_pendentes,
                melhor_proposta=melhor_proposta,
                data_limite=sol.data_limite_proposta,
                created_at=sol.created_at
            ))

            # Gerar alerta se todas as propostas foram recebidas
            if propostas_pendentes == 0 and propostas_recebidas > 0:
                alertas.append(AlertaResponse(
                    tipo="cotacao_completa",
                    prioridade="alta",
                    titulo=f"Cotacao {sol.numero} completa!",
                    mensagem=f"Todas as {propostas_recebidas} propostas foram recebidas. Clique para ver o mapa comparativo.",
                    link=f"/cotacoes/{sol.id}/mapa",
                    dados={
                        "solicitacao_id": sol.id,
                        "numero": sol.numero,
                        "propostas_recebidas": propostas_recebidas,
                        "melhor_proposta": melhor_proposta
                    },
                    created_at=now
                ))
            elif propostas_recebidas > 0:
                alertas.append(AlertaResponse(
                    tipo="propostas_recebidas",
                    prioridade="media",
                    titulo=f"Novas propostas em {sol.numero}",
                    mensagem=f"{propostas_recebidas} de {total_fornecedores} fornecedores responderam.",
                    link=f"/cotacoes/{sol.id}/propostas",
                    dados={
                        "solicitacao_id": sol.id,
                        "numero": sol.numero,
                        "propostas_recebidas": propostas_recebidas,
                        "total_fornecedores": total_fornecedores
                    },
                    created_at=now
                ))

    # 2. Verificar emails pendentes de classificacao
    emails_pendentes = db.query(func.count(EmailProcessado.id)).filter(
        EmailProcessado.tenant_id == tenant_id,
        EmailProcessado.status == 'pendente'
    ).scalar() or 0

    if emails_pendentes > 0:
        alertas.append(AlertaResponse(
            tipo="emails_pendentes",
            prioridade="media",
            titulo=f"{emails_pendentes} email(s) aguardando revisao",
            mensagem="Existem emails que precisam ser classificados manualmente.",
            link="/emails",
            dados={"quantidade": emails_pendentes},
            created_at=now
        ))

    # 3. Verificar cotacoes proximas do vencimento
    from datetime import timedelta
    data_limite_alerta = now + timedelta(days=2)

    cotacoes_vencendo = db.query(SolicitacaoCotacao).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status.in_([StatusSolicitacao.ENVIADA, StatusSolicitacao.EM_COTACAO]),
        SolicitacaoCotacao.data_limite_proposta.isnot(None),
        SolicitacaoCotacao.data_limite_proposta <= data_limite_alerta,
        SolicitacaoCotacao.data_limite_proposta >= now
    ).all()

    for sol in cotacoes_vencendo:
        dias_restantes = (sol.data_limite_proposta - now).days
        alertas.append(AlertaResponse(
            tipo="cotacao_vencendo",
            prioridade="alta" if dias_restantes <= 1 else "media",
            titulo=f"Cotacao {sol.numero} vence em {dias_restantes} dia(s)",
            mensagem=f"Prazo limite: {sol.data_limite_proposta.strftime('%d/%m/%Y')}",
            link=f"/cotacoes/{sol.id}/propostas",
            dados={
                "solicitacao_id": sol.id,
                "numero": sol.numero,
                "dias_restantes": dias_restantes
            },
            created_at=now
        ))

    # 4. Calcular estatisticas gerais
    cotacoes_pendentes = db.query(func.count(SolicitacaoCotacao.id)).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status == StatusSolicitacao.RASCUNHO
    ).scalar() or 0

    cotacoes_em_andamento = db.query(func.count(SolicitacaoCotacao.id)).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status.in_([StatusSolicitacao.ENVIADA, StatusSolicitacao.EM_COTACAO])
    ).scalar() or 0

    cotacoes_finalizadas = db.query(func.count(SolicitacaoCotacao.id)).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status == StatusSolicitacao.FINALIZADA
    ).scalar() or 0

    emails_classificados = db.query(func.count(EmailProcessado.id)).filter(
        EmailProcessado.tenant_id == tenant_id,
        EmailProcessado.status == 'classificado'
    ).scalar() or 0

    fornecedores_ativos = db.query(func.count(Fornecedor.id)).filter(
        Fornecedor.tenant_id == tenant_id,
        Fornecedor.ativo == True
    ).scalar() or 0

    produtos_cadastrados = db.query(func.count(Produto.id)).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True
    ).scalar() or 0

    stats = DashboardStatsResponse(
        cotacoes_pendentes=cotacoes_pendentes,
        cotacoes_em_andamento=cotacoes_em_andamento,
        cotacoes_finalizadas=cotacoes_finalizadas,
        emails_pendentes=emails_pendentes,
        emails_classificados=emails_classificados,
        fornecedores_ativos=fornecedores_ativos,
        produtos_cadastrados=produtos_cadastrados,
        total_compras_mes=0.0  # TODO: Calcular quando tivermos pedidos de compra
    )

    # Ordenar alertas por prioridade
    prioridade_ordem = {"alta": 0, "media": 1, "baixa": 2}
    alertas.sort(key=lambda a: prioridade_ordem.get(a.prioridade, 3))

    return AlertasResumoResponse(
        alertas=alertas,
        solicitacoes_com_respostas=solicitacoes_com_respostas,
        stats=stats
    )


@router.get("/stats")
def obter_estatisticas(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """Obter apenas as estatisticas do dashboard (endpoint leve)"""
    cotacoes_pendentes = db.query(func.count(SolicitacaoCotacao.id)).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status == StatusSolicitacao.RASCUNHO
    ).scalar() or 0

    cotacoes_em_andamento = db.query(func.count(SolicitacaoCotacao.id)).filter(
        SolicitacaoCotacao.tenant_id == tenant_id,
        SolicitacaoCotacao.status.in_([StatusSolicitacao.ENVIADA, StatusSolicitacao.EM_COTACAO])
    ).scalar() or 0

    emails_pendentes = db.query(func.count(EmailProcessado.id)).filter(
        EmailProcessado.tenant_id == tenant_id,
        EmailProcessado.status == 'pendente'
    ).scalar() or 0

    fornecedores_ativos = db.query(func.count(Fornecedor.id)).filter(
        Fornecedor.tenant_id == tenant_id,
        Fornecedor.ativo == True
    ).scalar() or 0

    produtos_cadastrados = db.query(func.count(Produto.id)).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True
    ).scalar() or 0

    return {
        "cotacoes_pendentes": cotacoes_pendentes,
        "cotacoes_em_andamento": cotacoes_em_andamento,
        "emails_pendentes": emails_pendentes,
        "fornecedores_ativos": fornecedores_ativos,
        "produtos_cadastrados": produtos_cadastrados
    }
