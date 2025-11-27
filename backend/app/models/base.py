from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class TenantMixin:
    """
    Mixin para adicionar tenant_id em TODAS as tabelas
    CRÍTICO para isolamento multi-tenant

    Todas as tabelas que herdam este mixin terão automaticamente:
    - tenant_id (foreign key para tenants.id)
    - relacionamento com Tenant
    """

    @declared_attr
    def tenant_id(cls):
        return Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)

    @declared_attr
    def tenant(cls):
        return relationship("Tenant", foreign_keys=[cls.tenant_id])


class TimestampMixin:
    """
    Mixin para campos de auditoria temporal
    Todas as tabelas terão created_at e updated_at
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditMixin:
    """
    Mixin para campos de auditoria de usuário
    Registra quem criou e quem atualizou
    Suporta soft delete (deleted_at)
    """

    @declared_attr
    def created_by(cls):
        return Column(Integer, ForeignKey('usuarios.id'), nullable=True)

    @declared_attr
    def updated_by(cls):
        return Column(Integer, ForeignKey('usuarios.id'), nullable=True)

    deleted_at = Column(DateTime, nullable=True)  # Soft delete


# Base já foi definida em database.py
# Aqui apenas importamos e exportamos para facilitar
__all__ = ['Base', 'TenantMixin', 'TimestampMixin', 'AuditMixin']
