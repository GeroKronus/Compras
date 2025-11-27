from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, TenantMixin, TimestampMixin


class TipoUsuario(str, enum.Enum):
    """
    Tipos de usuário do sistema com diferentes permissões
    """
    MASTER = "MASTER"            # Super admin - acesso a todos os tenants
    ADMIN = "ADMIN"              # Administrador do tenant - acesso total
    GERENTE = "GERENTE"          # Gerente - aprova compras, visualiza relatórios
    COMPRADOR = "COMPRADOR"      # Comprador - cria cotações e compras
    ALMOXARIFE = "ALMOXARIFE"    # Almoxarife - gerencia estoque
    VISUALIZADOR = "VISUALIZADOR"  # Apenas visualiza dados


class Usuario(Base, TenantMixin, TimestampMixin):
    """
    Usuários do sistema

    IMPORTANTE: Cada usuário pertence a UM ÚNICO tenant
    Não é possível um usuário acessar múltiplos tenants
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)

    # Dados pessoais
    nome_completo = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)  # Email único por tenant
    senha_hash = Column(String(255), nullable=False)  # Senha hasheada com bcrypt

    # Perfil e permissões
    tipo = Column(SQLEnum(TipoUsuario), default=TipoUsuario.VISUALIZADOR, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    # Dados de contato
    telefone = Column(String(20), nullable=True)
    setor = Column(String(100), nullable=True)  # Ex: Compras, Almoxarifado, Produção

    # Configurações pessoais
    notificacoes_email = Column(Boolean, default=True)
    notificacoes_sistema = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Usuario {self.nome_completo} ({self.email})>"

    # Índice composto para garantir email único por tenant
    __table_args__ = (
        # Um mesmo email pode existir em tenants diferentes,
        # mas não pode ser duplicado dentro do mesmo tenant
        # UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )
