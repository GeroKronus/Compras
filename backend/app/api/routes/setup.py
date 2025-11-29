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
        db = SessionLocal()
        try:
            from app.models.cotacao import SolicitacaoCotacao, PropostaFornecedor

            dados = {"solicitacoes": [], "propostas": []}

            # Solicitações via ORM
            solicitacoes = db.query(SolicitacaoCotacao).all()
            for s in solicitacoes:
                dados["solicitacoes"].append({
                    "id": s.id, "numero": s.numero, "titulo": s.titulo,
                    "status": s.status.value if s.status else None, "tenant_id": s.tenant_id
                })

            # Propostas via ORM
            propostas = db.query(PropostaFornecedor).all()
            for p in propostas:
                dados["propostas"].append({
                    "id": p.id, "solicitacao_id": p.solicitacao_id, "fornecedor_id": p.fornecedor_id,
                    "status": p.status.value if p.status else None,
                    "valor_total": float(p.valor_total) if p.valor_total else None,
                    "tenant_id": p.tenant_id
                })

            return dados
        finally:
            db.close()
    except Exception as e:
        import traceback
        return {"erro": str(e), "trace": traceback.format_exc()}


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
