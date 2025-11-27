"""
Rota de setup inicial do sistema.
Permite criar o primeiro usuário MASTER quando o banco está vazio.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from app.database import get_db, engine
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.usuario import Usuario, TipoUsuario
# Importar todos os models para que o Base.metadata conheça todas as tabelas
from app.models import categoria, produto, fornecedor, cotacao, pedido, auditoria
import bcrypt


def create_tables():
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
        # Tenta verificar se a tabela existe
        master_exists = db.query(Usuario).filter(
            Usuario.tipo == TipoUsuario.MASTER
        ).first() is not None

        return {
            "initialized": master_exists,
            "tables_created": True,
            "message": "Sistema já inicializado" if master_exists else "Sistema aguardando inicialização"
        }
    except Exception:
        # Tabelas não existem ainda
        return {
            "initialized": False,
            "tables_created": False,
            "message": "Tabelas não criadas. Use POST /api/v1/setup/init para inicializar."
        }


@router.post("/create-tables")
def create_database_tables():
    """
    Cria todas as tabelas no banco de dados.
    Seguro para executar múltiplas vezes (não recria tabelas existentes).
    """
    try:
        create_tables()
        return {"success": True, "message": "Tabelas criadas com sucesso!"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar tabelas: {str(e)}"
        )


@router.post("/init", response_model=SetupResponse)
def initialize_system(
    request: SetupRequest,
    db: Session = Depends(get_db)
):
    """
    Inicializa o sistema criando o tenant MASTER e o primeiro usuário MASTER.

    IMPORTANTE: Este endpoint só funciona se NÃO existir nenhum usuário MASTER.
    Após a primeira execução, ele retornará erro.

    Este endpoint automaticamente cria as tabelas se não existirem.
    """
    # Validar senha primeiro (antes de criar tabelas)
    if len(request.senha) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter pelo menos 8 caracteres"
        )

    try:
        # Criar tabelas se não existirem
        create_tables()

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
                ia_habilitada=True
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

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao inicializar sistema: {str(e)}"
        )
