from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TenantMixin, TimestampMixin, AuditMixin


class Categoria(Base, TenantMixin, TimestampMixin, AuditMixin):
    """
    Categorias de produtos com suporte a hierarquia

    Exemplo:
    - Discos Diamantados (categoria pai)
      - Discos para Granito (subcategoria)
      - Discos para Mármore (subcategoria)
    """
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)

    # Dados básicos
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    codigo = Column(String(20), nullable=True)  # Código interno opcional

    # Hierarquia (auto-referência)
    categoria_pai_id = Column(Integer, ForeignKey('categorias.id'), nullable=True)

    # Relacionamentos
    categoria_pai = relationship("Categoria", remote_side=[id], backref="subcategorias")
    produtos = relationship("Produto", back_populates="categoria")

    def __repr__(self):
        return f"<Categoria {self.nome}>"

    # Índices compostos para multi-tenant
    __table_args__ = (
        Index('idx_categorias_tenant_id', 'tenant_id', 'id'),
        Index('idx_categorias_tenant_nome', 'tenant_id', 'nome'),
        Index('idx_categorias_tenant_codigo', 'tenant_id', 'codigo'),
    )
