"""
Tabela de associação Produto <-> Fornecedor (N:N)
Cada produto pode ter múltiplos fornecedores
Cada fornecedor pode fornecer múltiplos produtos
"""
from sqlalchemy import Column, Integer, ForeignKey, Table, Index
from app.models.base import Base


# Tabela de associação (muitos para muitos)
produto_fornecedor = Table(
    'produto_fornecedor',
    Base.metadata,
    Column('produto_id', Integer, ForeignKey('produtos.id', ondelete='CASCADE'), primary_key=True),
    Column('fornecedor_id', Integer, ForeignKey('fornecedores.id', ondelete='CASCADE'), primary_key=True),
    Column('tenant_id', Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
    Index('idx_prod_forn_tenant', 'tenant_id'),
    Index('idx_prod_forn_produto', 'produto_id'),
    Index('idx_prod_forn_fornecedor', 'fornecedor_id'),
)
