"""
Rota de setup inicial do sistema.
Permite criar o primeiro usuário MASTER quando o banco está vazio.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db, engine, Base
from app.models.tenant import Tenant
from app.models.usuario import Usuario, TipoUsuario
# Importar todos os models para registrar no metadata
from app.models import (
    tenant, usuario, categoria, produto, fornecedor,
    cotacao, pedido, auditoria_escolha, uso_ia,
    email_processado, produto_fornecedor
)
import bcrypt


def create_all_tables():
    """Criar todas as tabelas no banco de dados"""
    Base.metadata.create_all(bind=engine)

router = APIRouter()


@router.get("/version")
def get_version():
    """Retorna versão do backend"""
    return {"version": "1.0036", "endpoint": "setup/version"}


class SetupRequest(BaseModel):
    """Schema para requisição de setup inicial"""
    email: EmailStr
    senha: str
    nome_completo: str


class SetupResponse(BaseModel):
    """Schema para resposta de setup"""
    success: bool
    message: str
    cnpj: str | None = None
    email: str | None = None


@router.get("/status")
def get_setup_status(db: Session = Depends(get_db)):
    """
    Verifica se o sistema já foi inicializado.
    Retorna se já existe um usuário MASTER.
    """
    try:
        master_exists = db.query(Usuario).filter(
            Usuario.tipo == TipoUsuario.MASTER
        ).first() is not None

        return {
            "initialized": master_exists,
            "message": "Sistema já inicializado" if master_exists else "Sistema aguardando inicialização - use POST /api/v1/setup/init"
        }
    except Exception as e:
        return {
            "initialized": False,
            "error": str(e),
            "message": "Erro ao verificar status. As tabelas podem ainda estar sendo criadas."
        }


@router.post("/init", response_model=SetupResponse)
def initialize_system(
    request: SetupRequest,
    db: Session = Depends(get_db)
):
    """
    Inicializa o sistema criando o tenant MASTER e o primeiro usuário MASTER.

    IMPORTANTE: Este endpoint só funciona se NÃO existir nenhum usuário MASTER.
    Após a primeira execução, ele retornará erro.

    As tabelas são criadas automaticamente no startup da aplicação.
    """
    # Validar senha primeiro
    if len(request.senha) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 8 caracteres"
        )

    try:
        # Criar tabelas primeiro (se não existirem)
        create_all_tables()

        # Verificar se já existe um usuário MASTER
        master_exists = db.query(Usuario).filter(
            Usuario.tipo == TipoUsuario.MASTER
        ).first()

        if master_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sistema já foi inicializado. Não é possível criar outro usuário MASTER por este endpoint."
            )

        # Criar ou recuperar tenant MASTER
        tenant = db.query(Tenant).filter(Tenant.slug == "master").first()

        if not tenant:
            tenant = Tenant(
                nome_empresa="Sistema Master",
                razao_social="Administração do Sistema",
                cnpj="00000000000000",
                slug="master",
                ativo=True,
                plano="enterprise",
                max_usuarios=999,
                max_produtos=99999,
                max_fornecedores=99999,
                ia_habilitada=True,
                email_contato=request.email  # Usar email do admin como contato
            )
            db.add(tenant)
            db.flush()

        # Hash da senha
        senha_hash = bcrypt.hashpw(
            request.senha.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Criar usuário MASTER
        usuario = Usuario(
            tenant_id=tenant.id,
            nome_completo=request.nome_completo,
            email=request.email,
            senha_hash=senha_hash,
            tipo=TipoUsuario.MASTER,
            ativo=True,
            notificacoes_email=True,
            notificacoes_sistema=True
        )
        db.add(usuario)
        db.commit()

        return SetupResponse(
            success=True,
            message="Sistema inicializado com sucesso! Use o CNPJ e email para fazer login.",
            cnpj="00000000000000",
            email=request.email
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao inicializar sistema: {str(e)}"
        )


@router.get("/diagnostico")
def diagnostico_cotacoes():
    """
    Endpoint temporário de diagnóstico para verificar estado das cotações.
    SEM AUTENTICAÇÃO - apenas para debug.
    """
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            dados = {"solicitacoes": [], "propostas": [], "contagens": {}, "tenants": []}

            # Contagem direta via SQL
            count_sol = db.execute(text("SELECT COUNT(*) FROM solicitacoes_cotacao")).scalar()
            count_prop = db.execute(text("SELECT COUNT(*) FROM propostas_fornecedor")).scalar()
            dados["contagens"] = {"solicitacoes": count_sol, "propostas": count_prop}

            # Solicitações via SQL
            sol_rows = db.execute(text("SELECT id, numero, titulo, status, tenant_id FROM solicitacoes_cotacao")).fetchall()
            for row in sol_rows:
                dados["solicitacoes"].append({
                    "id": row[0], "numero": row[1], "titulo": row[2],
                    "status": str(row[3]) if row[3] else None, "tenant_id": row[4]
                })

            # Propostas via SQL
            prop_rows = db.execute(text("SELECT id, solicitacao_id, fornecedor_id, status, valor_total, tenant_id FROM propostas_fornecedor")).fetchall()
            for row in prop_rows:
                dados["propostas"].append({
                    "id": row[0], "solicitacao_id": row[1], "fornecedor_id": row[2],
                    "status": str(row[3]) if row[3] else None,
                    "valor_total": float(row[4]) if row[4] else None,
                    "tenant_id": row[5]
                })

            # Itens proposta via SQL
            dados["itens_proposta"] = []
            itens_prop_rows = db.execute(text("SELECT id, proposta_id, item_solicitacao_id, preco_unitario, tenant_id FROM itens_proposta")).fetchall()
            for row in itens_prop_rows:
                dados["itens_proposta"].append({
                    "id": row[0], "proposta_id": row[1], "item_solicitacao_id": row[2],
                    "preco_unitario": float(row[3]) if row[3] else None,
                    "tenant_id": row[4]
                })

            # Itens solicitacao via SQL
            dados["itens_solicitacao"] = []
            itens_sol_rows = db.execute(text("SELECT id, solicitacao_id, produto_id, quantidade, tenant_id FROM itens_solicitacao")).fetchall()
            for row in itens_sol_rows:
                dados["itens_solicitacao"].append({
                    "id": row[0], "solicitacao_id": row[1], "produto_id": row[2],
                    "quantidade": float(row[3]) if row[3] else None,
                    "tenant_id": row[4]
                })

            return dados
        finally:
            db.close()
    except Exception as e:
        import traceback
        return {"erro": str(e), "trace": traceback.format_exc()}


@router.get("/debug-propostas/{solicitacao_id}")
def debug_propostas(solicitacao_id: int):
    """
    DEBUG: Simula o endpoint de propostas sem autenticação.
    Testa EXATAMENTE a mesma lógica do endpoint real incluindo _enrich_proposta_response.
    """
    try:
        from app.database import SessionLocal
        from app.models.cotacao import SolicitacaoCotacao, PropostaFornecedor, ItemProposta, ItemSolicitacao
        from app.models.fornecedor import Fornecedor
        from app.models.produto import Produto

        db = SessionLocal()
        try:
            # Buscar solicitacao
            solicitacao = db.query(SolicitacaoCotacao).filter(
                SolicitacaoCotacao.id == solicitacao_id
            ).first()

            if not solicitacao:
                return {"erro": f"Solicitacao {solicitacao_id} nao encontrada"}

            # Buscar propostas SEM filtro tenant_id (igual ao endpoint corrigido)
            propostas = db.query(PropostaFornecedor).filter(
                PropostaFornecedor.solicitacao_id == solicitacao_id
            ).all()

            # Montar resposta usando a mesma lógica de _enrich_proposta_response
            items = []
            erros = []

            for proposta in propostas:
                try:
                    fornecedor = db.query(Fornecedor).filter(Fornecedor.id == proposta.fornecedor_id).first()

                    # Processar itens da proposta (igual ao _enrich_proposta_response)
                    itens = []
                    for item in proposta.itens:
                        item_solic = db.query(ItemSolicitacao).filter(ItemSolicitacao.id == item.item_solicitacao_id).first()
                        produto = db.query(Produto).filter(Produto.id == item_solic.produto_id).first() if item_solic else None

                        itens.append({
                            "id": item.id, "proposta_id": item.proposta_id, "item_solicitacao_id": item.item_solicitacao_id,
                            "preco_unitario": float(item.preco_unitario) if item.preco_unitario else None,
                            "quantidade_disponivel": float(item.quantidade_disponivel) if item.quantidade_disponivel else None,
                            "desconto_percentual": float(item.desconto_percentual) if item.desconto_percentual else None,
                            "preco_final": float(item.preco_final) if item.preco_final else None,
                            "prazo_entrega_item": item.prazo_entrega_item, "observacoes": item.observacoes,
                            "marca_oferecida": item.marca_oferecida, "tenant_id": item.tenant_id,
                            "produto_nome": produto.nome if produto else None,
                            "quantidade_solicitada": float(item_solic.quantidade) if item_solic else None
                        })

                    items.append({
                        "id": proposta.id, "solicitacao_id": proposta.solicitacao_id, "fornecedor_id": proposta.fornecedor_id,
                        "status": str(proposta.status) if proposta.status else None,
                        "data_envio_solicitacao": str(proposta.data_envio_solicitacao) if proposta.data_envio_solicitacao else None,
                        "data_recebimento": str(proposta.data_recebimento) if proposta.data_recebimento else None,
                        "condicoes_pagamento": proposta.condicoes_pagamento,
                        "prazo_entrega": proposta.prazo_entrega,
                        "validade_proposta": str(proposta.validade_proposta) if proposta.validade_proposta else None,
                        "valor_total": float(proposta.valor_total) if proposta.valor_total else None,
                        "desconto_total": float(proposta.desconto_total) if proposta.desconto_total else 0,
                        "frete_tipo": proposta.frete_tipo, "frete_valor": float(proposta.frete_valor) if proposta.frete_valor else None,
                        "observacoes": proposta.observacoes,
                        "score_preco": float(proposta.score_preco) if proposta.score_preco else None,
                        "score_prazo": float(proposta.score_prazo) if proposta.score_prazo else None,
                        "score_condicoes": float(proposta.score_condicoes) if proposta.score_condicoes else None,
                        "score_total": float(proposta.score_total) if proposta.score_total else None,
                        "tenant_id": proposta.tenant_id,
                        "itens": itens, "fornecedor_nome": fornecedor.razao_social if fornecedor else None,
                        "fornecedor_cnpj": fornecedor.cnpj if fornecedor else None
                    })
                except Exception as e:
                    import traceback
                    erros.append({"proposta_id": proposta.id, "erro": str(e), "trace": traceback.format_exc()})

            return {
                "solicitacao": {"id": solicitacao.id, "numero": solicitacao.numero, "tenant_id": solicitacao.tenant_id},
                "items": items,
                "total": len(items),
                "erros": erros
            }
        finally:
            db.close()
    except Exception as e:
        import traceback
        return {"erro": str(e), "traceback": traceback.format_exc()}


@router.post("/corrigir-tenant-ids")
def corrigir_tenant_ids(db: Session = Depends(get_db)):
    """
    Endpoint para corrigir tenant_ids das propostas e itens.
    Sincroniza o tenant_id das propostas com o tenant_id da solicitação correspondente.
    SEM AUTENTICAÇÃO - apenas para debug/correção.
    """
    try:
        from sqlalchemy import text

        correcoes = []

        # 1. Corrigir propostas: tenant_id deve ser igual ao da solicitação
        update_propostas = text("""
            UPDATE propostas_fornecedor p
            SET tenant_id = s.tenant_id
            FROM solicitacoes_cotacao s
            WHERE p.solicitacao_id = s.id
            AND p.tenant_id != s.tenant_id
        """)
        result1 = db.execute(update_propostas)
        correcoes.append(f"Propostas corrigidas: {result1.rowcount}")

        # 2. Corrigir itens_proposta: tenant_id deve ser igual ao da proposta
        update_itens = text("""
            UPDATE itens_proposta ip
            SET tenant_id = p.tenant_id
            FROM propostas_fornecedor p
            WHERE ip.proposta_id = p.id
            AND ip.tenant_id != p.tenant_id
        """)
        result2 = db.execute(update_itens)
        correcoes.append(f"Itens proposta corrigidos: {result2.rowcount}")

        # 3. Corrigir itens_solicitacao: tenant_id deve ser igual ao da solicitação
        update_itens_sol = text("""
            UPDATE itens_solicitacao i
            SET tenant_id = s.tenant_id
            FROM solicitacoes_cotacao s
            WHERE i.solicitacao_id = s.id
            AND i.tenant_id != s.tenant_id
        """)
        result3 = db.execute(update_itens_sol)
        correcoes.append(f"Itens solicitacao corrigidos: {result3.rowcount}")

        db.commit()

        return {
            "sucesso": True,
            "correcoes": correcoes,
            "mensagem": "Tenant IDs sincronizados com sucesso"
        }

    except Exception as e:
        db.rollback()
        import traceback
        return {"erro": str(e), "tipo": type(e).__name__, "traceback": traceback.format_exc()}
