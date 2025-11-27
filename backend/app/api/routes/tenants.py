from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.tenant import Tenant
from app.models.usuario import Usuario, TipoUsuario
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.core.security import hash_password
from app.api.deps import get_current_tenant, get_current_user, require_admin
import re

router = APIRouter()


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
