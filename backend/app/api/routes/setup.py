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
from app.models.cotacao import (
    SolicitacaoCotacao, PropostaFornecedor, ItemProposta, ItemSolicitacao,
    StatusSolicitacao, StatusProposta
)
from app.models.fornecedor import Fornecedor
from app.models.produto import Produto
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
def diagnostico_cotacoes(db: Session = Depends(get_db)):
    """
    Endpoint temporário de diagnóstico para verificar estado das cotações.
    SEM AUTENTICAÇÃO - apenas para debug.
    """
    try:
        # Buscar todas as solicitações
        solicitacoes = db.query(SolicitacaoCotacao).all()

        result = {
            "total_solicitacoes": len(solicitacoes),
            "solicitacoes": []
        }

        for sol in solicitacoes:
            # Buscar propostas desta solicitação
            propostas = db.query(PropostaFornecedor).filter(
                PropostaFornecedor.solicitacao_id == sol.id
            ).all()

            # Buscar itens da solicitação
            itens_sol = db.query(ItemSolicitacao).filter(
                ItemSolicitacao.solicitacao_id == sol.id
            ).all()

            propostas_data = []
            for prop in propostas:
                # Buscar fornecedor
                forn = db.query(Fornecedor).filter(Fornecedor.id == prop.fornecedor_id).first()

                # Buscar itens da proposta
                itens_prop = db.query(ItemProposta).filter(
                    ItemProposta.proposta_id == prop.id
                ).all()

                propostas_data.append({
                    "id": prop.id,
                    "fornecedor_id": prop.fornecedor_id,
                    "fornecedor_nome": forn.razao_social if forn else "N/A",
                    "status": prop.status.value if prop.status else None,
                    "valor_total": float(prop.valor_total) if prop.valor_total else None,
                    "data_envio": str(prop.data_envio) if prop.data_envio else None,
                    "total_itens": len(itens_prop),
                    "itens": [
                        {
                            "produto_id": item.produto_id,
                            "quantidade": float(item.quantidade) if item.quantidade else None,
                            "preco_unitario": float(item.preco_unitario) if item.preco_unitario else None
                        }
                        for item in itens_prop
                    ]
                })

            result["solicitacoes"].append({
                "id": sol.id,
                "numero": sol.numero,
                "titulo": sol.titulo,
                "status": sol.status.value if sol.status else None,
                "tenant_id": sol.tenant_id,
                "data_abertura": str(sol.data_abertura) if sol.data_abertura else None,
                "total_itens": len(itens_sol),
                "total_propostas": len(propostas),
                "propostas": propostas_data
            })

        return result

    except Exception as e:
        return {"erro": str(e), "tipo": type(e).__name__}
