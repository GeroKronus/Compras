from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TenantMixin, TimestampMixin, AuditMixin


class Fornecedor(Base, TenantMixin, TimestampMixin, AuditMixin):
    """
    Fornecedores de produtos e serviços

    Armazena dados completos do fornecedor incluindo:
    - Dados cadastrais (CNPJ, endereço)
    - Múltiplos contatos
    - Condições comerciais
    - Avaliações e histórico
    """
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)

    # Dados cadastrais
    razao_social = Column(String(200), nullable=False)
    nome_fantasia = Column(String(200), nullable=True)
    cnpj = Column(String(14), nullable=False)  # Apenas números
    inscricao_estadual = Column(String(20), nullable=True)

    # Endereço
    endereco_logradouro = Column(String(200), nullable=True)
    endereco_numero = Column(String(20), nullable=True)
    endereco_complemento = Column(String(100), nullable=True)
    endereco_bairro = Column(String(100), nullable=True)
    endereco_cidade = Column(String(100), nullable=True)
    endereco_estado = Column(String(2), nullable=True)  # UF
    endereco_cep = Column(String(8), nullable=True)  # Apenas números

    # Contatos (JSON para suportar múltiplos contatos)
    contatos = Column(JSON, nullable=True)
    # Exemplo: [
    #   {"nome": "João Silva", "cargo": "Vendedor", "telefone": "11999999999", "email": "joao@fornecedor.com"},
    #   {"nome": "Maria Santos", "cargo": "Gerente", "telefone": "11888888888", "email": "maria@fornecedor.com"}
    # ]

    # Telefone e email principal (para queries rápidas)
    telefone_principal = Column(String(20), nullable=True)
    email_principal = Column(String(200), nullable=True)
    website = Column(String(200), nullable=True)

    # Condições comerciais
    prazo_entrega_medio = Column(Integer, nullable=True)  # Dias
    condicoes_pagamento = Column(Text, nullable=True)  # Ex: "30/60 dias", "À vista"
    valor_minimo_pedido = Column(Numeric(10, 2), nullable=True)
    frete_tipo = Column(String(20), nullable=True)  # CIF, FOB

    # Avaliação e performance
    rating = Column(Numeric(3, 2), default=0)  # 0.00 a 5.00
    total_compras = Column(Integer, default=0)  # Quantidade de compras realizadas
    valor_total_comprado = Column(Numeric(12, 2), default=0)  # Valor total histórico

    # Status
    ativo = Column(Boolean, default=True, nullable=False)
    aprovado = Column(Boolean, default=False)  # Fornecedor aprovado para compras

    # Observações
    observacoes = Column(Text, nullable=True)

    # Categorias de produtos que fornece (JSON) - DEPRECATED, usar relacionamento categorias
    categorias_produtos = Column(JSON, nullable=True)

    # Relacionamento com produtos que este fornecedor oferece
    produtos = relationship("Produto", secondary="produto_fornecedor", back_populates="fornecedores")

    # Relacionamento com categorias que este fornecedor atende
    categorias = relationship("Categoria", secondary="categoria_fornecedor", back_populates="fornecedores")

    def __repr__(self):
        return f"<Fornecedor {self.razao_social} - CNPJ: {self.cnpj}>"

    # Índices compostos para multi-tenant e performance
    __table_args__ = (
        Index('idx_fornecedores_tenant_id', 'tenant_id', 'id'),
        Index('idx_fornecedores_tenant_cnpj', 'tenant_id', 'cnpj'),
        Index('idx_fornecedores_tenant_razao', 'tenant_id', 'razao_social'),
        Index('idx_fornecedores_tenant_ativo', 'tenant_id', 'ativo'),
        Index('idx_fornecedores_tenant_aprovado', 'tenant_id', 'aprovado'),
    )
