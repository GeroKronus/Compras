from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import date, datetime
import re


class TenantBase(BaseModel):
    """Schema base para Tenant"""
    nome_empresa: str = Field(..., min_length=3, max_length=200)
    razao_social: str = Field(..., min_length=3, max_length=200)
    cnpj: str = Field(..., min_length=14, max_length=14)
    email_contato: EmailStr
    telefone: Optional[str] = None

    @validator('cnpj')
    def validate_cnpj(cls, v):
        """Valida formato do CNPJ (apenas números)"""
        if not re.match(r'^\d{14}$', v):
            raise ValueError('CNPJ deve conter exatamente 14 dígitos numéricos')
        return v


class TenantCreate(TenantBase):
    """Schema para criar um novo Tenant"""
    plano: str = Field(default='trial', pattern='^(trial|basic|pro|enterprise)$')

    # Dados do primeiro usuário (admin)
    admin_nome: str = Field(..., min_length=3, max_length=200)
    admin_email: EmailStr
    admin_senha: str = Field(..., min_length=8)

    @validator('admin_senha')
    def validate_senha(cls, v):
        """Valida força da senha"""
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('Senha deve conter pelo menos um número')
        return v


class TenantUpdate(BaseModel):
    """Schema para atualizar Tenant"""
    nome_empresa: Optional[str] = Field(None, min_length=3, max_length=200)
    razao_social: Optional[str] = Field(None, min_length=3, max_length=200)
    email_contato: Optional[EmailStr] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = None
    plano: Optional[str] = Field(None, pattern='^(trial|basic|pro|enterprise)$')
    ia_habilitada: Optional[bool] = None
    ia_auto_aprovacao: Optional[bool] = None
    ia_limite_auto_aprovacao: Optional[float] = None
    compartilhar_dados_agregados: Optional[bool] = None


class TenantResponse(TenantBase):
    """Schema de resposta para Tenant"""
    id: int
    slug: str
    ativo: bool
    plano: str
    data_expiracao: Optional[date] = None
    ia_habilitada: bool
    ia_auto_aprovacao: bool
    ia_limite_auto_aprovacao: float
    compartilhar_dados_agregados: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (antes era orm_mode)
