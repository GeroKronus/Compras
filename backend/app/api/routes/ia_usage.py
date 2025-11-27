"""
Rotas de Controle de Uso da IA
Dashboard de creditos e estatisticas
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel
from app.api.deps import get_db, get_current_tenant_id, get_current_user
from app.models.usuario import Usuario
from app.services.ia_usage_service import ia_usage_service

router = APIRouter()


# ============ SCHEMAS ============

class LimitesUpdateRequest(BaseModel):
    tokens_limite: Optional[int] = None
    chamadas_limite: Optional[int] = None
    custo_limite: Optional[float] = None
    chave_propria: Optional[str] = None
    usar_chave_propria: Optional[bool] = None


# ============ ENDPOINTS ============

@router.get("/verificar")
def verificar_limite_uso(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Verifica se o tenant pode fazer mais chamadas a IA.

    Retorna:
    - pode_usar: se o tenant ainda pode usar a IA
    - mensagem: motivo se nao puder
    - uso_atual: dados de uso do mes
    """
    pode_usar, mensagem, uso_atual = ia_usage_service.verificar_limite(db, tenant_id)

    return {
        "pode_usar": pode_usar,
        "mensagem": mensagem,
        "uso_atual": uso_atual
    }


@router.get("/estatisticas")
def obter_estatisticas_uso(
    mes: Optional[str] = Query(None, description="Mes no formato YYYY-MM (padrao: atual)"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Obter estatisticas detalhadas de uso da IA no mes.

    Retorna:
    - total de chamadas, tokens e custo
    - detalhamento por tipo de operacao
    - limites e disponibilidade
    - percentuais de uso
    """
    return ia_usage_service.obter_estatisticas_mes(db, tenant_id, mes)


@router.get("/dashboard")
def dashboard_uso_ia(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Dashboard completo de uso da IA.

    Retorna dados formatados para exibicao no frontend:
    - Resumo de uso do mes
    - Limites e disponibilidade
    - Grafico de uso por tipo
    - Alertas se proximo do limite
    """
    estatisticas = ia_usage_service.obter_estatisticas_mes(db, tenant_id)

    # Montar alertas
    alertas = []

    if estatisticas["percentuais"]["tokens"] >= 90:
        alertas.append({
            "tipo": "warning",
            "mensagem": f"Uso de tokens em {estatisticas['percentuais']['tokens']}% do limite mensal"
        })
    elif estatisticas["percentuais"]["tokens"] >= 100:
        alertas.append({
            "tipo": "error",
            "mensagem": "Limite de tokens atingido! IA desabilitada."
        })

    if estatisticas["percentuais"]["chamadas"] >= 90:
        alertas.append({
            "tipo": "warning",
            "mensagem": f"Uso de chamadas em {estatisticas['percentuais']['chamadas']}% do limite mensal"
        })

    if estatisticas["percentuais"]["custo"] >= 90:
        alertas.append({
            "tipo": "warning",
            "mensagem": f"Custo em {estatisticas['percentuais']['custo']}% do limite mensal"
        })

    # Verificar disponibilidade
    pode_usar, mensagem, uso_atual = ia_usage_service.verificar_limite(db, tenant_id)

    return {
        "mes_referencia": estatisticas["mes"],
        "resumo": {
            "chamadas": {
                "usado": estatisticas["total_chamadas"],
                "limite": estatisticas["limites"]["chamadas_limite"],
                "disponivel": estatisticas["limites"]["chamadas_disponivel"],
                "percentual": estatisticas["percentuais"]["chamadas"]
            },
            "tokens": {
                "usado": estatisticas["total_tokens"],
                "limite": estatisticas["limites"]["tokens_limite"],
                "disponivel": estatisticas["limites"]["tokens_disponivel"],
                "percentual": estatisticas["percentuais"]["tokens"]
            },
            "custo": {
                "usado": estatisticas["total_custo"],
                "limite": estatisticas["limites"]["custo_limite"],
                "disponivel": estatisticas["limites"]["custo_disponivel"],
                "percentual": estatisticas["percentuais"]["custo"]
            }
        },
        "por_tipo": estatisticas["por_tipo"],
        "status": {
            "ia_disponivel": pode_usar,
            "mensagem": mensagem
        },
        "alertas": alertas
    }


@router.get("/historico")
def historico_uso_ia(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Historico de chamadas a IA.

    Filtros:
    - tipo: analise_proposta, extracao_email, classificacao_email
    """
    from app.models.uso_ia import UsoIA
    from sqlalchemy import desc

    query = db.query(UsoIA).filter(UsoIA.tenant_id == tenant_id)

    if tipo:
        query = query.filter(UsoIA.tipo_operacao == tipo)

    total = query.count()
    query = query.order_by(desc(UsoIA.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    registros = query.all()

    items = []
    for reg in registros:
        items.append({
            "id": reg.id,
            "tipo_operacao": reg.tipo_operacao,
            "modelo": reg.modelo,
            "tokens_entrada": reg.tokens_entrada,
            "tokens_saida": reg.tokens_saida,
            "tokens_total": reg.tokens_total,
            "custo_estimado": float(reg.custo_estimado),
            "referencia_id": reg.referencia_id,
            "referencia_tipo": reg.referencia_tipo,
            "descricao": reg.descricao,
            "usuario_id": reg.usuario_id,
            "created_at": reg.created_at
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.put("/limites")
def atualizar_limites_ia(
    dados: LimitesUpdateRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualizar limites de uso da IA do tenant.

    Permite configurar:
    - Limite de tokens mensais
    - Limite de chamadas mensais
    - Limite de custo mensal
    - Chave API propria (opcional)
    """
    # Verificar se usuario e admin (somente admins podem alterar limites)
    from app.models.usuario import TipoUsuario
    if current_user.tipo not in [TipoUsuario.ADMIN, TipoUsuario.GESTOR]:
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar limites")

    custo_limite = Decimal(str(dados.custo_limite)) if dados.custo_limite else None

    limite = ia_usage_service.atualizar_limites(
        db,
        tenant_id,
        tokens_limite=dados.tokens_limite,
        chamadas_limite=dados.chamadas_limite,
        custo_limite=custo_limite,
        chave_propria=dados.chave_propria,
        usar_chave_propria=dados.usar_chave_propria
    )

    return {
        "sucesso": True,
        "mensagem": "Limites atualizados",
        "limites": {
            "tokens_mensais": limite.tokens_mensais_limite,
            "chamadas_mensais": limite.chamadas_mensais_limite,
            "custo_mensal": float(limite.custo_mensal_limite),
            "usando_chave_propria": limite.usar_chave_propria
        }
    }


@router.get("/limites")
def obter_limites_ia(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Obter configuracao de limites do tenant.
    """
    from app.models.uso_ia import LimiteIATenant

    limite = db.query(LimiteIATenant).filter(
        LimiteIATenant.tenant_id == tenant_id
    ).first()

    if not limite:
        # Retornar valores padrao
        return {
            "tokens_mensais_limite": 100000,
            "chamadas_mensais_limite": 500,
            "custo_mensal_limite": 10.00,
            "usando_chave_propria": False,
            "tem_chave_propria": False
        }

    return {
        "tokens_mensais_limite": limite.tokens_mensais_limite,
        "chamadas_mensais_limite": limite.chamadas_mensais_limite,
        "custo_mensal_limite": float(limite.custo_mensal_limite),
        "usando_chave_propria": limite.usar_chave_propria,
        "tem_chave_propria": bool(limite.chave_api_propria)
    }
