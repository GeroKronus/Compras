from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.usuario import Usuario, TipoUsuario


def get_db():
    """
    Dependency para obter sessão do banco de dados
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_tenant_id(request: Request) -> int:
    """
    Extrai tenant_id do contexto da request (configurado pelo middleware)
    """
    if not hasattr(request.state, 'tenant_id'):
        raise HTTPException(status_code=400, detail="Tenant não identificado")
    return request.state.tenant_id


def get_current_user_id(request: Request) -> int:
    """
    Extrai user_id do contexto da request
    """
    if not hasattr(request.state, 'user_id'):
        raise HTTPException(status_code=400, detail="Usuário não identificado")
    return request.state.user_id


def get_current_tenant(
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Retorna objeto Tenant completo do tenant atual
    Valida se o tenant está ativo
    """
    tenant = db.query(Tenant).filter_by(id=tenant_id, ativo=True).first()
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada ou inativa"
        )
    return tenant


def get_current_user(
    user_id: int = Depends(get_current_user_id),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Retorna objeto Usuario completo do usuário atual
    Valida se o usuário pertence ao tenant e está ativo
    """
    user = db.query(Usuario).filter_by(
        id=user_id,
        tenant_id=tenant_id,
        ativo=True
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado ou inativo"
        )

    return user


def require_master(
    user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Dependency que requer que o usuário seja MASTER (super admin)
    """
    if user.tipo != TipoUsuario.MASTER:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: apenas usuário master"
        )
    return user


def require_admin(
    user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Dependency que requer que o usuário seja ADMIN ou MASTER
    """
    if user.tipo not in [TipoUsuario.ADMIN, TipoUsuario.MASTER]:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: apenas administradores"
        )
    return user


def require_gerente_or_admin(
    user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Dependency que requer que o usuário seja GERENTE, ADMIN ou MASTER
    """
    if user.tipo not in [TipoUsuario.GERENTE, TipoUsuario.ADMIN, TipoUsuario.MASTER]:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: permissão insuficiente"
        )
    return user
