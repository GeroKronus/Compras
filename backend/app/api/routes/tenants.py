from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.tenant import Tenant
from app.models.usuario import Usuario, TipoUsuario
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.core.security import hash_password
from app.api.deps import get_current_tenant, get_current_user, require_admin, require_master
import re

router = APIRouter()


# =============================================
# SCHEMAS PARA ENDPOINTS DO MASTER
# =============================================

class TenantListItem(BaseModel):
    id: int
    nome_empresa: str
    razao_social: str
    cnpj: str
    slug: str
    ativo: bool
    plano: str
    ia_habilitada: bool
    email_contato: str
    telefone: Optional[str]
    total_usuarios: int
    created_at: str

    class Config:
        from_attributes = True


class MasterStats(BaseModel):
    total_tenants: int
    tenants_ativos: int
    total_usuarios: int
    tenants_trial: int


class MasterCreateTenant(BaseModel):
    nome_empresa: str
    razao_social: str
    cnpj: str
    email_contato: EmailStr
    telefone: Optional[str] = None
    plano: str = "trial"
    admin_nome: str
    admin_email: EmailStr
    admin_senha: str


class ToggleTenantRequest(BaseModel):
    ativo: bool


def generate_slug(nome_empresa: str) -> str:
    """
    Gera um slug URL-friendly a partir do nome da empresa
    Ex: "Empresa XYZ Ltda" -> "empresa-xyz-ltda"
    """
    slug = nome_empresa.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)  # Remove caracteres especiais
    slug = re.sub(r'[-\s]+', '-', slug)   # Substitui espaços por hífen
    slug = slug.strip('-')                 # Remove hífens das pontas
    return slug


@router.post("/register", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def register_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db)
):
    """
    Registra um novo tenant (empresa) no sistema

    ROTA PÚBLICA - permite auto-registro

    Cria:
    1. O tenant (empresa)
    2. O primeiro usuário admin da empresa
    """

    # Verificar se CNPJ já existe
    existing_tenant = db.query(Tenant).filter_by(cnpj=tenant_data.cnpj).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CNPJ já cadastrado"
        )

    # Gerar slug único
    base_slug = generate_slug(tenant_data.nome_empresa)
    slug = base_slug
    counter = 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Criar tenant
    new_tenant = Tenant(
        nome_empresa=tenant_data.nome_empresa,
        razao_social=tenant_data.razao_social,
        cnpj=tenant_data.cnpj,
        slug=slug,
        email_contato=tenant_data.email_contato,
        telefone=tenant_data.telefone,
        plano=tenant_data.plano,
        ativo=True,
        ia_habilitada=True,
        compartilhar_dados_agregados=True
    )

    db.add(new_tenant)
    db.flush()  # Para obter o ID do tenant

    # Criar usuário admin
    admin_user = Usuario(
        tenant_id=new_tenant.id,
        nome_completo=tenant_data.admin_nome,
        email=tenant_data.admin_email,
        senha_hash=hash_password(tenant_data.admin_senha),
        tipo=TipoUsuario.ADMIN,
        ativo=True
    )

    db.add(admin_user)
    db.commit()
    db.refresh(new_tenant)

    return new_tenant


@router.get("/me", response_model=TenantResponse)
def get_my_tenant(
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Retorna dados do tenant atual (empresa do usuário logado)
    """
    return tenant


@router.patch("/me", response_model=TenantResponse)
def update_my_tenant(
    tenant_update: TenantUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    user: Usuario = Depends(require_admin),  # Apenas admin pode atualizar
    db: Session = Depends(get_db)
):
    """
    Atualiza dados do tenant atual

    Apenas usuários ADMIN podem atualizar
    """

    # Atualizar campos fornecidos
    update_data = tenant_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(tenant, field, value)

    db.commit()
    db.refresh(tenant)

    return tenant


@router.get("/stats")
def get_tenant_stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Retorna estatísticas de uso do tenant

    Ex: quantos usuários, produtos, fornecedores cadastrados
    e se está próximo dos limites do plano
    """

    total_usuarios = db.query(Usuario).filter_by(tenant_id=tenant.id).count()

    return {
        "tenant_id": tenant.id,
        "nome_empresa": tenant.nome_empresa,
        "plano": tenant.plano,
        "uso": {
            "usuarios": {
                "atual": total_usuarios,
                "limite": tenant.max_usuarios,
                "percentual": (total_usuarios / tenant.max_usuarios * 100) if tenant.max_usuarios > 0 else 0
            },
            # Produtos e fornecedores serão implementados nas próximas fases
        }
    }


# =============================================
# ENDPOINTS EXCLUSIVOS PARA MASTER
# =============================================

@router.get("/master/stats", response_model=MasterStats)
def get_master_stats(
    user: Usuario = Depends(require_master),
    db: Session = Depends(get_db)
):
    """
    Retorna estatisticas globais do sistema (apenas MASTER)
    """
    # Excluir o tenant MASTER das contagens
    total_tenants = db.query(Tenant).filter(Tenant.slug != "master").count()
    tenants_ativos = db.query(Tenant).filter(
        Tenant.slug != "master",
        Tenant.ativo == True
    ).count()
    tenants_trial = db.query(Tenant).filter(
        Tenant.slug != "master",
        Tenant.plano == "trial"
    ).count()

    # Total de usuarios (excluindo MASTER)
    total_usuarios = db.query(Usuario).join(Tenant).filter(
        Tenant.slug != "master"
    ).count()

    return MasterStats(
        total_tenants=total_tenants,
        tenants_ativos=tenants_ativos,
        total_usuarios=total_usuarios,
        tenants_trial=tenants_trial
    )


@router.get("/master/list", response_model=List[TenantListItem])
def list_all_tenants(
    user: Usuario = Depends(require_master),
    db: Session = Depends(get_db)
):
    """
    Lista todos os tenants do sistema (apenas MASTER)
    """
    # Buscar tenants com contagem de usuarios
    tenants = db.query(Tenant).filter(Tenant.slug != "master").all()

    result = []
    for tenant in tenants:
        total_usuarios = db.query(Usuario).filter_by(tenant_id=tenant.id).count()
        result.append(TenantListItem(
            id=tenant.id,
            nome_empresa=tenant.nome_empresa,
            razao_social=tenant.razao_social,
            cnpj=tenant.cnpj,
            slug=tenant.slug,
            ativo=tenant.ativo,
            plano=tenant.plano,
            ia_habilitada=tenant.ia_habilitada,
            email_contato=tenant.email_contato or "",
            telefone=tenant.telefone,
            total_usuarios=total_usuarios,
            created_at=tenant.created_at.isoformat() if tenant.created_at else ""
        ))

    return result


@router.post("/master/create", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def master_create_tenant(
    tenant_data: MasterCreateTenant,
    user: Usuario = Depends(require_master),
    db: Session = Depends(get_db)
):
    """
    Cria um novo tenant com seu admin (apenas MASTER)
    """
    # Limpar CNPJ (remover pontuacao)
    cnpj_limpo = re.sub(r'\D', '', tenant_data.cnpj)

    # Verificar se CNPJ ja existe
    existing_tenant = db.query(Tenant).filter_by(cnpj=cnpj_limpo).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CNPJ ja cadastrado"
        )

    # Verificar se email do admin ja existe
    existing_email = db.query(Usuario).filter_by(email=tenant_data.admin_email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email do administrador ja cadastrado"
        )

    # Gerar slug unico
    base_slug = generate_slug(tenant_data.nome_empresa)
    slug = base_slug
    counter = 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Criar tenant
    new_tenant = Tenant(
        nome_empresa=tenant_data.nome_empresa,
        razao_social=tenant_data.razao_social,
        cnpj=cnpj_limpo,
        slug=slug,
        email_contato=tenant_data.email_contato,
        telefone=tenant_data.telefone,
        plano=tenant_data.plano,
        ativo=True,
        ia_habilitada=True,
        compartilhar_dados_agregados=True
    )

    db.add(new_tenant)
    db.flush()

    # Criar usuario admin
    admin_user = Usuario(
        tenant_id=new_tenant.id,
        nome_completo=tenant_data.admin_nome,
        email=tenant_data.admin_email,
        senha_hash=hash_password(tenant_data.admin_senha),
        tipo=TipoUsuario.ADMIN,
        ativo=True
    )

    db.add(admin_user)
    db.commit()
    db.refresh(new_tenant)

    return new_tenant


@router.patch("/master/{tenant_id}/toggle")
def toggle_tenant_status(
    tenant_id: int,
    request: ToggleTenantRequest,
    user: Usuario = Depends(require_master),
    db: Session = Depends(get_db)
):
    """
    Ativa/desativa um tenant (apenas MASTER)
    """
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada"
        )

    # Nao permitir desativar o tenant MASTER
    if tenant.slug == "master":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao e possivel alterar o tenant master"
        )

    tenant.ativo = request.ativo
    db.commit()

    return {
        "success": True,
        "message": f"Empresa {'ativada' if request.ativo else 'desativada'} com sucesso"
    }
