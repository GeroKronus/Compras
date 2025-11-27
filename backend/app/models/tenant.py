from sqlalchemy import Column, Integer, String, Boolean, Date, Numeric
from app.models.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    """
    Representa uma empresa cliente do SaaS (Multi-Tenant)

    Cada tenant é uma empresa independente com:
    - Seus próprios usuários
    - Seus próprios dados isolados
    - Configurações específicas
    - Limites de uso por plano
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação
    nome_empresa = Column(String(200), nullable=False)
    razao_social = Column(String(200), nullable=False)
    cnpj = Column(String(14), unique=True, nullable=False, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)  # URL-friendly (ex: "empresa-xyz")

    # Status da conta
    ativo = Column(Boolean, default=True, nullable=False)
    plano = Column(String(20), default='trial')  # trial, basic, pro, enterprise
    data_expiracao = Column(Date, nullable=True)  # Data de expiração do plano

    # Limites por plano
    max_usuarios = Column(Integer, default=5)
    max_produtos = Column(Integer, default=1000)
    max_fornecedores = Column(Integer, default=100)

    # Configurações de IA
    ia_habilitada = Column(Boolean, default=True)
    ia_auto_aprovacao = Column(Boolean, default=False)  # IA pode auto-aprovar compras?
    ia_limite_auto_aprovacao = Column(Numeric(10, 2), default=2000.00)  # Limite em R$ para auto-aprovação

    # IMPORTANTE: Opt-in para compartilhar dados agregados
    # Se False, os dados desta empresa NÃO serão incluídos no knowledge base coletivo
    compartilhar_dados_agregados = Column(Boolean, default=True)

    # Contato
    email_contato = Column(String(200), nullable=False)
    telefone = Column(String(20), nullable=True)

    def __repr__(self):
        return f"<Tenant {self.nome_empresa} (ID: {self.id})>"
