"""
Rotas de Auditoria - Escolhas divergentes de fornecedor
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from decimal import Decimal

from app.api.deps import get_db, get_current_tenant_id, get_current_user, require_admin
from app.models.auditoria_escolha import AuditoriaEscolhaFornecedor
from app.models.usuario import Usuario

router = APIRouter()


# ============ SCHEMAS ============

class AuditoriaEscolhaResponse(BaseModel):
    id: int
    solicitacao_id: int
    solicitacao_numero: str
    fornecedor_escolhido_nome: str
    valor_escolhido: float
    fornecedor_recomendado_nome: str
    valor_recomendado: float
    diferenca_valor: float
    diferenca_percentual: float
    justificativa: str
    usuario_nome: Optional[str]
    data_escolha: datetime
    revisado_admin: bool
    observacao_admin: Optional[str]

    class Config:
        from_attributes = True


class AuditoriaListResponse(BaseModel):
    items: List[AuditoriaEscolhaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RevisarAuditoriaRequest(BaseModel):
    observacao: Optional[str] = None


class EstatisticasAuditoriaResponse(BaseModel):
    total_divergencias: int
    total_nao_revisadas: int
    valor_total_diferenca: float
    media_diferenca_percentual: float


# ============ ENDPOINTS ============

@router.get("/escolhas-divergentes", response_model=AuditoriaListResponse)
def listar_escolhas_divergentes(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    apenas_nao_revisadas: bool = Query(False, description="Filtrar apenas não revisadas"),
    solicitacao_numero: Optional[str] = Query(None, description="Filtrar por número da solicitação")
):
    """
    Listar todas as escolhas que divergiram da recomendação (menor preço)
    """
    query = db.query(AuditoriaEscolhaFornecedor).filter(
        AuditoriaEscolhaFornecedor.tenant_id == tenant_id
    )

    if apenas_nao_revisadas:
        query = query.filter(AuditoriaEscolhaFornecedor.revisado_admin == False)

    if solicitacao_numero:
        query = query.filter(AuditoriaEscolhaFornecedor.solicitacao_numero.ilike(f"%{solicitacao_numero}%"))

    # Ordenar por data mais recente
    query = query.order_by(desc(AuditoriaEscolhaFornecedor.data_escolha))

    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return AuditoriaListResponse(
        items=[
            AuditoriaEscolhaResponse(
                id=item.id,
                solicitacao_id=item.solicitacao_id,
                solicitacao_numero=item.solicitacao_numero,
                fornecedor_escolhido_nome=item.fornecedor_escolhido_nome,
                valor_escolhido=float(item.valor_escolhido),
                fornecedor_recomendado_nome=item.fornecedor_recomendado_nome,
                valor_recomendado=float(item.valor_recomendado),
                diferenca_valor=float(item.diferenca_valor),
                diferenca_percentual=float(item.diferenca_percentual),
                justificativa=item.justificativa,
                usuario_nome=item.usuario_nome,
                data_escolha=item.data_escolha,
                revisado_admin=item.revisado_admin or False,
                observacao_admin=item.observacao_admin
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/escolhas-divergentes/estatisticas", response_model=EstatisticasAuditoriaResponse)
def estatisticas_auditoria(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Obter estatísticas das escolhas divergentes
    """
    from sqlalchemy import func

    # Total de divergências
    total_divergencias = db.query(func.count(AuditoriaEscolhaFornecedor.id)).filter(
        AuditoriaEscolhaFornecedor.tenant_id == tenant_id
    ).scalar() or 0

    # Não revisadas
    total_nao_revisadas = db.query(func.count(AuditoriaEscolhaFornecedor.id)).filter(
        AuditoriaEscolhaFornecedor.tenant_id == tenant_id,
        AuditoriaEscolhaFornecedor.revisado_admin == False
    ).scalar() or 0

    # Valor total da diferença
    valor_total = db.query(func.sum(AuditoriaEscolhaFornecedor.diferenca_valor)).filter(
        AuditoriaEscolhaFornecedor.tenant_id == tenant_id
    ).scalar() or 0

    # Média percentual
    media_percentual = db.query(func.avg(AuditoriaEscolhaFornecedor.diferenca_percentual)).filter(
        AuditoriaEscolhaFornecedor.tenant_id == tenant_id
    ).scalar() or 0

    return EstatisticasAuditoriaResponse(
        total_divergencias=total_divergencias,
        total_nao_revisadas=total_nao_revisadas,
        valor_total_diferenca=float(valor_total),
        media_diferenca_percentual=float(media_percentual)
    )


@router.get("/escolhas-divergentes/{auditoria_id}", response_model=AuditoriaEscolhaResponse)
def obter_auditoria(
    auditoria_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Obter detalhes de uma auditoria específica
    """
    auditoria = db.query(AuditoriaEscolhaFornecedor).filter(
        AuditoriaEscolhaFornecedor.id == auditoria_id,
        AuditoriaEscolhaFornecedor.tenant_id == tenant_id
    ).first()

    if not auditoria:
        raise HTTPException(status_code=404, detail="Registro de auditoria não encontrado")

    return AuditoriaEscolhaResponse(
        id=auditoria.id,
        solicitacao_id=auditoria.solicitacao_id,
        solicitacao_numero=auditoria.solicitacao_numero,
        fornecedor_escolhido_nome=auditoria.fornecedor_escolhido_nome,
        valor_escolhido=float(auditoria.valor_escolhido),
        fornecedor_recomendado_nome=auditoria.fornecedor_recomendado_nome,
        valor_recomendado=float(auditoria.valor_recomendado),
        diferenca_valor=float(auditoria.diferenca_valor),
        diferenca_percentual=float(auditoria.diferenca_percentual),
        justificativa=auditoria.justificativa,
        usuario_nome=auditoria.usuario_nome,
        data_escolha=auditoria.data_escolha,
        revisado_admin=auditoria.revisado_admin or False,
        observacao_admin=auditoria.observacao_admin
    )


@router.post("/escolhas-divergentes/{auditoria_id}/revisar", response_model=AuditoriaEscolhaResponse)
def revisar_auditoria(
    auditoria_id: int,
    request: RevisarAuditoriaRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Marcar auditoria como revisada pelo admin
    """
    auditoria = db.query(AuditoriaEscolhaFornecedor).filter(
        AuditoriaEscolhaFornecedor.id == auditoria_id,
        AuditoriaEscolhaFornecedor.tenant_id == tenant_id
    ).first()

    if not auditoria:
        raise HTTPException(status_code=404, detail="Registro de auditoria não encontrado")

    auditoria.revisado_admin = True
    auditoria.data_revisao = datetime.utcnow()
    auditoria.observacao_admin = request.observacao

    db.commit()
    db.refresh(auditoria)

    return AuditoriaEscolhaResponse(
        id=auditoria.id,
        solicitacao_id=auditoria.solicitacao_id,
        solicitacao_numero=auditoria.solicitacao_numero,
        fornecedor_escolhido_nome=auditoria.fornecedor_escolhido_nome,
        valor_escolhido=float(auditoria.valor_escolhido),
        fornecedor_recomendado_nome=auditoria.fornecedor_recomendado_nome,
        valor_recomendado=float(auditoria.valor_recomendado),
        diferenca_valor=float(auditoria.diferenca_valor),
        diferenca_percentual=float(auditoria.diferenca_percentual),
        justificativa=auditoria.justificativa,
        usuario_nome=auditoria.usuario_nome,
        data_escolha=auditoria.data_escolha,
        revisado_admin=auditoria.revisado_admin or False,
        observacao_admin=auditoria.observacao_admin
    )
