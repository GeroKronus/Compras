from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioLogin, Token, UsuarioResponse
from app.schemas.tenant import TenantResponse
from app.core.security import verify_password, create_access_token
from datetime import timedelta
from app.config import settings

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    credentials: UsuarioLogin,
    db: Session = Depends(get_db)
):
    """
    Autenticação de usuário

    Fluxo:
    1. Identifica o tenant pelo CNPJ
    2. Busca o usuário pelo email dentro daquele tenant
    3. Verifica a senha
    4. Gera JWT token com tenant_id e user_id
    """

    # 1. Buscar tenant pelo CNPJ
    tenant = db.query(Tenant).filter_by(cnpj=credentials.cnpj, ativo=True).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CNPJ não encontrado ou empresa inativa"
        )

    # 2. Buscar usuário pelo email dentro do tenant
    usuario = db.query(Usuario).filter_by(
        email=credentials.email,
        tenant_id=tenant.id,
        ativo=True
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    # 3. Verificar senha
    if not verify_password(credentials.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    # 4. Gerar token JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "user_id": usuario.id,
            "tenant_id": tenant.id,
            "tipo": usuario.tipo.value,
            "email": usuario.email
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UsuarioResponse.from_orm(usuario),
        "tenant": {
            "id": tenant.id,
            "nome_empresa": tenant.nome_empresa,
            "slug": tenant.slug,
            "plano": tenant.plano,
            "ia_habilitada": tenant.ia_habilitada
        }
    }


@router.post("/refresh")
def refresh_token(
    # TODO: Implementar refresh token
):
    """
    Renova o token JWT
    (A implementar)
    """
    pass
