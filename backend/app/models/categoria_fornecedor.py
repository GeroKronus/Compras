"""
Tabela de associação Categoria <-> Fornecedor (N:N)
Cada categoria pode ter múltiplos fornecedores
Cada fornecedor pode atender múltiplas categorias
"""
from sqlalchemy import Column, Integer, ForeignKey, Table, Index
from app.models.base import Base


# Tabela de associação (muitos para muitos)
categoria_fornecedor = Table(
    'categoria_fornecedor',
    Base.metadata,
    Column('categoria_id', Integer, ForeignKey('categorias.id', ondelete='CASCADE'), primary_key=True),
    Column('fornecedor_id', Integer, ForeignKey('fornecedores.id', ondelete='CASCADE'), primary_key=True),
    Column('tenant_id', Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
    Index('idx_cat_forn_tenant', 'tenant_id'),
    Index('idx_cat_forn_categoria', 'categoria_id'),
    Index('idx_cat_forn_fornecedor', 'fornecedor_id'),
)
