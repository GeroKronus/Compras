from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from app.models.usuario import TipoUsuario
import re


class UsuarioBase(BaseModel):
    """Schema base para Usuario"""
    nome_completo: str = Field(..., min_length=3, max_length=200)
    email: EmailStr
    telefone: Optional[str] = None
    setor: Optional[str] = Field(None, max_length=100)


class UsuarioCreate(UsuarioBase):
    """Schema para criar um novo Usuario"""
    senha: str = Field(..., min_length=8)
    tipo: TipoUsuario = TipoUsuario.VISUALIZADOR

    @validator('senha')
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


class UsuarioUpdate(BaseModel):
    """Schema para atualizar Usuario"""
    nome_completo: Optional[str] = Field(None, min_length=3, max_length=200)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    setor: Optional[str] = None
    tipo: Optional[TipoUsuario] = None
    ativo: Optional[bool] = None
    notificacoes_email: Optional[bool] = None
    notificacoes_sistema: Optional[bool] = None


class UsuarioUpdateSenha(BaseModel):
    """Schema para atualizar senha"""
    senha_atual: str
    senha_nova: str = Field(..., min_length=8)
    senha_nova_confirmacao: str

    @validator('senha_nova')
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

    @validator('senha_nova_confirmacao')
    def senhas_match(cls, v, values):
        if 'senha_nova' in values and v != values['senha_nova']:
            raise ValueError('Senhas não conferem')
        return v


class UsuarioResponse(UsuarioBase):
    """Schema de resposta para Usuario (SEM senha!)"""
    id: int
    tenant_id: int
    tipo: TipoUsuario
    ativo: bool
    notificacoes_email: bool
    notificacoes_sistema: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsuarioLogin(BaseModel):
    """Schema para login"""
    email: EmailStr
    senha: str
    cnpj: str = Field(..., min_length=14, max_length=14)  # Necessário para identificar o tenant

    @validator('cnpj')
    def validate_cnpj(cls, v):
        """Valida formato do CNPJ"""
        if not re.match(r'^\d{14}$', v):
            raise ValueError('CNPJ deve conter exatamente 14 dígitos numéricos')
        return v


class Token(BaseModel):
    """Schema de resposta para autenticação"""
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse
    tenant: dict
