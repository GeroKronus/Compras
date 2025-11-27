"""
Rotas de Gestão de Usuários

- MASTER: pode criar usuários em qualquer tenant (especialmente ADMINs)
- ADMIN: pode criar/gerenciar usuários no próprio tenant
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import bcrypt

from app.api.deps import (
    get_db, get_current_tenant_id, get_current_user,
    require_admin, require_master
)
from app.models.usuario import Usuario, TipoUsuario
from app.models.tenant import Tenant
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse

router = APIRouter()


# ============ SCHEMAS ADICIONAIS ============

class UsuarioCreateByAdmin(BaseModel):
    """Schema para admin criar usuário no próprio tenant"""
    nome_completo: str = Field(..., min_length=3, max_length=200)
    email: EmailStr
    senha: str = Field(..., min_length=8)
    tipo: TipoUsuario = TipoUsuario.COMPRADOR
    telefone: Optional[str] = None
    setor: Optional[str] = None


class UsuarioCreateByMaster(BaseModel):
    """Schema para master criar usuário em qualquer tenant"""
    nome_completo: str = Field(..., min_length=3, max_length=200)
    email: EmailStr
    senha: str = Field(..., min_length=8)
    tipo: TipoUsuario = TipoUsuario.ADMIN
    tenant_id: int  # Master pode especificar o tenant
    telefone: Optional[str] = None
    setor: Optional[str] = None


class UsuarioListResponse(BaseModel):
    items: List[UsuarioResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(..., min_length=8)


class ResetarSenhaRequest(BaseModel):
    nova_senha: str = Field(..., min_length=8)


# ============ ENDPOINTS PARA ADMIN ============

@router.get("", response_model=UsuarioListResponse)
def listar_usuarios(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tipo: Optional[TipoUsuario] = None,
    ativo: Optional[bool] = None,
    search: Optional[str] = None
):
    """
    Listar usuários do tenant (requer ADMIN ou MASTER)
    """
    query = db.query(Usuario).filter(Usuario.tenant_id == tenant_id)

    # Filtros
    if tipo:
        query = query.filter(Usuario.tipo == tipo)
    if ativo is not None:
        query = query.filter(Usuario.ativo == ativo)
    if search:
        query = query.filter(
            (Usuario.nome_completo.ilike(f"%{search}%")) |
            (Usuario.email.ilike(f"%{search}%"))
        )

    # Ordenação e paginação
    query = query.order_by(desc(Usuario.created_at))
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return UsuarioListResponse(
        items=[UsuarioResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("", response_model=UsuarioResponse)
def criar_usuario(
    data: UsuarioCreateByAdmin,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Criar novo usuário no tenant (requer ADMIN ou MASTER)

    ADMIN não pode criar usuários MASTER ou ADMIN (apenas MASTER pode)
    """
    # Verificar se ADMIN está tentando criar MASTER ou ADMIN
    if current_user.tipo == TipoUsuario.ADMIN:
        if data.tipo in [TipoUsuario.MASTER, TipoUsuario.ADMIN]:
            raise HTTPException(
                status_code=403,
                detail="Apenas MASTER pode criar usuários ADMIN ou MASTER"
            )

    # Verificar se email já existe no tenant
    existing = db.query(Usuario).filter(
        Usuario.tenant_id == tenant_id,
        Usuario.email == data.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado nesta empresa"
        )

    # Hash da senha
    senha_hash = bcrypt.hashpw(data.senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Criar usuário
    usuario = Usuario(
        tenant_id=tenant_id,
        nome_completo=data.nome_completo,
        email=data.email,
        senha_hash=senha_hash,
        tipo=data.tipo,
        telefone=data.telefone,
        setor=data.setor,
        ativo=True
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return UsuarioResponse.model_validate(usuario)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obter_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Obter detalhes de um usuário (requer ADMIN ou MASTER)
    """
    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id,
        Usuario.tenant_id == tenant_id
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return UsuarioResponse.model_validate(usuario)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def atualizar_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Atualizar usuário (requer ADMIN ou MASTER)
    """
    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id,
        Usuario.tenant_id == tenant_id
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # ADMIN não pode alterar tipo para MASTER/ADMIN
    if current_user.tipo == TipoUsuario.ADMIN:
        if data.tipo in [TipoUsuario.MASTER, TipoUsuario.ADMIN]:
            raise HTTPException(
                status_code=403,
                detail="Apenas MASTER pode promover usuários a ADMIN ou MASTER"
            )
        # ADMIN não pode alterar outro ADMIN
        if usuario.tipo == TipoUsuario.ADMIN and usuario.id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Apenas MASTER pode alterar outros administradores"
            )

    # Verificar email único se estiver alterando
    if data.email and data.email != usuario.email:
        existing = db.query(Usuario).filter(
            Usuario.tenant_id == tenant_id,
            Usuario.email == data.email,
            Usuario.id != usuario_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email já está em uso")

    # Atualizar campos
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(usuario, field, value)

    db.commit()
    db.refresh(usuario)

    return UsuarioResponse.model_validate(usuario)


@router.post("/{usuario_id}/desativar", response_model=UsuarioResponse)
def desativar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Desativar usuário (requer ADMIN ou MASTER)
    """
    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id,
        Usuario.tenant_id == tenant_id
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if usuario.id == current_user.id:
        raise HTTPException(status_code=400, detail="Não é possível desativar a si mesmo")

    # ADMIN não pode desativar outro ADMIN
    if current_user.tipo == TipoUsuario.ADMIN and usuario.tipo == TipoUsuario.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Apenas MASTER pode desativar administradores"
        )

    usuario.ativo = False
    db.commit()
    db.refresh(usuario)

    return UsuarioResponse.model_validate(usuario)


@router.post("/{usuario_id}/ativar", response_model=UsuarioResponse)
def ativar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Reativar usuário (requer ADMIN ou MASTER)
    """
    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id,
        Usuario.tenant_id == tenant_id
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    usuario.ativo = True
    db.commit()
    db.refresh(usuario)

    return UsuarioResponse.model_validate(usuario)


@router.post("/{usuario_id}/resetar-senha", response_model=UsuarioResponse)
def resetar_senha_usuario(
    usuario_id: int,
    data: ResetarSenhaRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: Usuario = Depends(require_admin)
):
    """
    Resetar senha de um usuário (requer ADMIN ou MASTER)
    """
    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id,
        Usuario.tenant_id == tenant_id
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # ADMIN não pode resetar senha de outro ADMIN
    if current_user.tipo == TipoUsuario.ADMIN and usuario.tipo == TipoUsuario.ADMIN:
        if usuario.id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Apenas MASTER pode resetar senha de administradores"
            )

    # Hash da nova senha
    senha_hash = bcrypt.hashpw(data.nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    usuario.senha_hash = senha_hash

    db.commit()
    db.refresh(usuario)

    return UsuarioResponse.model_validate(usuario)


# ============ ENDPOINTS PARA MASTER ============

@router.post("/master/criar-admin", response_model=UsuarioResponse)
def criar_admin_em_tenant(
    data: UsuarioCreateByMaster,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_master)
):
    """
    Criar usuário ADMIN em qualquer tenant (apenas MASTER)

    Este endpoint permite ao MASTER criar administradores para empresas clientes.
    """
    # Verificar se o tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id, Tenant.ativo == True).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa não encontrada ou inativa")

    # Verificar se email já existe no tenant
    existing = db.query(Usuario).filter(
        Usuario.tenant_id == data.tenant_id,
        Usuario.email == data.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado nesta empresa"
        )

    # Hash da senha
    senha_hash = bcrypt.hashpw(data.senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Criar usuário
    usuario = Usuario(
        tenant_id=data.tenant_id,
        nome_completo=data.nome_completo,
        email=data.email,
        senha_hash=senha_hash,
        tipo=data.tipo,
        telefone=data.telefone,
        setor=data.setor,
        ativo=True
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return UsuarioResponse.model_validate(usuario)


@router.get("/master/todos-usuarios", response_model=UsuarioListResponse)
def listar_todos_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_master),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[int] = None,
    tipo: Optional[TipoUsuario] = None,
    search: Optional[str] = None
):
    """
    Listar usuários de todos os tenants (apenas MASTER)
    """
    query = db.query(Usuario)

    # Filtros
    if tenant_id:
        query = query.filter(Usuario.tenant_id == tenant_id)
    if tipo:
        query = query.filter(Usuario.tipo == tipo)
    if search:
        query = query.filter(
            (Usuario.nome_completo.ilike(f"%{search}%")) |
            (Usuario.email.ilike(f"%{search}%"))
        )

    # Ordenação e paginação
    query = query.order_by(desc(Usuario.created_at))
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return UsuarioListResponse(
        items=[UsuarioResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


# ============ ENDPOINTS PARA O PRÓPRIO USUÁRIO ============

@router.get("/me", response_model=UsuarioResponse)
def obter_meu_perfil(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter dados do próprio usuário logado
    """
    return UsuarioResponse.model_validate(current_user)


@router.put("/me", response_model=UsuarioResponse)
def atualizar_meu_perfil(
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualizar dados do próprio perfil (não pode alterar tipo ou ativo)
    """
    # Usuário não pode alterar seu próprio tipo ou status ativo
    if data.tipo is not None or data.ativo is not None:
        raise HTTPException(
            status_code=403,
            detail="Não é possível alterar seu próprio tipo ou status"
        )

    # Verificar email único se estiver alterando
    if data.email and data.email != current_user.email:
        existing = db.query(Usuario).filter(
            Usuario.tenant_id == current_user.tenant_id,
            Usuario.email == data.email,
            Usuario.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email já está em uso")

    # Atualizar campos
    update_data = data.model_dump(exclude_unset=True, exclude={'tipo', 'ativo'})
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return UsuarioResponse.model_validate(current_user)


@router.post("/me/alterar-senha")
def alterar_minha_senha(
    data: AlterarSenhaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Alterar a própria senha (requer senha atual)
    """
    # Verificar senha atual
    if not bcrypt.checkpw(data.senha_atual.encode('utf-8'), current_user.senha_hash.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    # Hash da nova senha
    senha_hash = bcrypt.hashpw(data.nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    current_user.senha_hash = senha_hash

    db.commit()

    return {"message": "Senha alterada com sucesso"}
