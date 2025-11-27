from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TenantMixin, TimestampMixin, AuditMixin
from app.models.produto_fornecedor import produto_fornecedor


class Produto(Base, TenantMixin, TimestampMixin, AuditMixin):
    """
    Produtos/Insumos do sistema

    Exemplos:
    - Disco Diamantado 350mm
    - Resina Epóxi
    - Abrasivo Grão 60
    - Peça de reposição para Politriz
    """
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação
    codigo = Column(String(50), nullable=False)  # Código interno da empresa
    nome = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)

    # Categoria
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=True)

    # Unidade de medida
    unidade_medida = Column(String(20), nullable=False, default="UN")  # UN, KG, M, L, CX, etc

    # Controle de estoque
    estoque_minimo = Column(Numeric(10, 2), default=0)
    estoque_maximo = Column(Numeric(10, 2), nullable=True)
    estoque_atual = Column(Numeric(10, 2), default=0)

    # Preço referência (última compra ou média)
    preco_referencia = Column(Numeric(10, 2), nullable=True)

    # Especificações técnicas (JSON flexível)
    especificacoes = Column(JSON, nullable=True)
    # Exemplo: {
    #   "diametro": "350mm",
    #   "espessura": "3mm",
    #   "aplicacao": "Granito",
    #   "marca": "Diamantec"
    # }

    # Imagem
    imagem_url = Column(String(500), nullable=True)

    # Status
    ativo = Column(Boolean, default=True, nullable=False)

    # Observações
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    categoria = relationship("Categoria", back_populates="produtos")
    fornecedores = relationship("Fornecedor", secondary=produto_fornecedor, back_populates="produtos")

    def __repr__(self):
        return f"<Produto {self.codigo} - {self.nome}>"

    # Índices compostos para multi-tenant e performance
    __table_args__ = (
        Index('idx_produtos_tenant_id', 'tenant_id', 'id'),
        Index('idx_produtos_tenant_codigo', 'tenant_id', 'codigo'),
        Index('idx_produtos_tenant_nome', 'tenant_id', 'nome'),
        Index('idx_produtos_tenant_categoria', 'tenant_id', 'categoria_id'),
        Index('idx_produtos_tenant_ativo', 'tenant_id', 'ativo'),
    )
