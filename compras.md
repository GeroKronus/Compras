# SISTEMA DE GESTÃO DE COMPRAS E ESTOQUE - MULTI-TENANT COM IA

## VISÃO GERAL DO PROJETO

Você é um arquiteto de software especializado em sistemas ERP para indústrias. Sua missão é desenvolver um **Sistema de Gestão de Compras e Estoque SaaS** para empresas do setor de mineração, beneficiamento de mármores e granitos.

### Diferenciais do Sistema:
1. **Multi-Tenant**: Múltiplas empresas usando a mesma infraestrutura com isolamento total de dados
2. **Agente IA Inteligente**: Análise automática de cotações usando conhecimento coletivo anonimizado
3. **Inteligência de Mercado**: Benchmarks agregados de todas as empresas para melhores decisões
4. **Privacidade por Design**: Dados isolados por empresa, conhecimento compartilhado anonimizado

---

## PERFIL DO NEGÓCIO

- **Setor**: Mineração e beneficiamento de rochas ornamentais (mármores e granitos)
- **Porte**: Empresas médias (50-200 funcionários)
- **Ambiente**: Industrial com múltiplos setores (produção, estoque, expedição)
- **Criticidade**: Sistemas de produção não podem parar por falta de insumos
- **Usuários**: Compradores, almoxarifes, supervisores, gerentes, diretores
- **Modelo de Negócio**: SaaS B2B (múltiplas empresas assinantes)

### Características Operacionais do Setor:
1. **Insumos Críticos**: Discos diamantados, resinas, abrasivos, granalhas
2. **Equipamentos**: Politrizes, teares, pontes rolantes, talhas, compressores
3. **Manutenção**: Peças de reposição específicas por equipamento
4. **Fornecedores**: Mix de locais, nacionais e importadores
5. **Urgências**: Compras emergenciais são frequentes (quebras, imprevistos)
6. **Variabilidade**: Produtos similares com especificações técnicas diferentes

---

# STACK TECNOLÓGICA

## Backend
- **FastAPI** (Python 3.11+)
- **SQLAlchemy** 2.0+ (ORM)
- **Alembic** (migrações de banco)
- **Pydantic** v2 (validação de dados)
- **PostgreSQL** (banco de dados)
  - **Railway** para hospedagem (desenvolvimento e produção)
- **psycopg2-binary** (driver PostgreSQL)
- **python-dotenv** (variáveis de ambiente)
- **python-jose[cryptography]** (JWT)
- **passlib[bcrypt]** (hash de senhas)
- **Anthropic API** (Claude para IA)

## Frontend
- **React** 18+ com **TypeScript**
- **Vite** (build tool)
- **TanStack Query** (React Query - gerenciamento de estado servidor)
- **React Hook Form** + **Zod** (formulários e validação)
- **Tailwind CSS** (estilização)
- **Shadcn/ui** (componentes)
- **Axios** (HTTP client)
- **React Router** (navegação)
- **Recharts** (gráficos)

## Infraestrutura
- **Railway** para PostgreSQL e deploy
- **Docker** (opcional para desenvolvimento local)
- Variáveis de ambiente (.env)
- GitHub para versionamento

---

# ESTRUTURA DO PROJETO
```
sistema-compras-saas/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py          # JWT, hashing
│   │   │   └── tenant_context.py    # Gerenciamento de tenant
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── tenant_middleware.py # Isolamento multi-tenant
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base + Mixins
│   │   │   ├── tenant.py            # Empresas
│   │   │   ├── usuario.py
│   │   │   ├── produto.py
│   │   │   ├── categoria.py
│   │   │   ├── fornecedor.py
│   │   │   ├── cotacao.py
│   │   │   ├── compra.py
│   │   │   ├── estoque.py
│   │   │   ├── ia_knowledge.py      # IA - Conhecimento agregado
│   │   │   └── audit.py             # Logs de auditoria
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py
│   │   │   ├── usuario.py
│   │   │   ├── produto.py
│   │   │   ├── fornecedor.py
│   │   │   ├── cotacao.py
│   │   │   ├── compra.py
│   │   │   └── estoque.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py              # Dependencies
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py          # Login, registro
│   │   │       ├── tenants.py       # Gestão de empresas
│   │   │       ├── produtos.py
│   │   │       ├── fornecedores.py
│   │   │       ├── cotacoes.py
│   │   │       ├── compras.py
│   │   │       ├── estoque.py
│   │   │       ├── ia_analise.py    # Endpoints IA
│   │   │       └── relatorios.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── compra_service.py
│   │   │   ├── estoque_service.py
│   │   │   ├── cotacao_service.py
│   │   │   ├── aprovacao_service.py
│   │   │   ├── ia_agente_service.py        # Agente IA principal
│   │   │   └── ia_agregacao_service.py     # Agregação de conhecimento
│   │   │
│   │   ├── jobs/
│   │   │   ├── __init__.py
│   │   │   ├── agregacao_ia.py      # Job diário de agregação
│   │   │   └── alertas_estoque.py   # Job alertas
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── validators.py
│   │       └── notifications.py
│   │
│   ├── alembic/
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_api/
│   │
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                  # Shadcn components
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── forms/
│   │   │   ├── tables/
│   │   │   └── ia/
│   │   │       ├── AnaliseCotacaoIA.tsx
│   │   │       └── BenchmarkMercado.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   │   └── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Produtos/
│   │   │   ├── Fornecedores/
│   │   │   ├── Cotacoes/
│   │   │   ├── Compras/
│   │   │   ├── Estoque/
│   │   │   ├── Relatorios/
│   │   │   └── Configuracoes/
│   │   │       └── ConfiguracaoIA.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useTenant.ts
│   │   │   └── useApi.ts
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── ia-service.ts
│   │   │
│   │   ├── types/
│   │   │   └── index.ts
│   │   │
│   │   ├── utils/
│   │   │   └── format.ts
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── public/
│   ├── .env.example
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── README.md
│
├── .gitignore
└── README.md
```

---

# CONFIGURAÇÃO DO AMBIENTE

## Variáveis de Ambiente

### Backend (.env)
```env
# Database (Railway PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# JWT
SECRET_KEY=sua-chave-secreta-muito-forte-aqui-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API
API_V1_STR=/api/v1
PROJECT_NAME=Sistema de Compras Multi-Tenant
ENVIRONMENT=development

# CORS (separado por vírgula)
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Anthropic AI
ANTHROPIC_API_KEY=sua-chave-anthropic-api-aqui

# Jobs
ENABLE_SCHEDULED_JOBS=true
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Dependências

### Backend (requirements.txt)
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
email-validator==2.1.0
anthropic==0.8.1
apscheduler==3.10.4
```

### Frontend (package.json - principais)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.12.0",
    "react-hook-form": "^7.48.0",
    "zod": "^3.22.0",
    "@hookform/resolvers": "^3.3.0",
    "axios": "^1.6.0",
    "tailwindcss": "^3.3.0",
    "recharts": "^2.10.0"
  }
}
```

---

# ARQUITETURA MULTI-TENANT

## Conceito

Múltiplas empresas (tenants) usam a mesma aplicação com **isolamento total de dados**:
- Empresa A vê APENAS seus dados
- Empresa B vê APENAS seus dados
- IA aprende com TODOS mas de forma ANONIMIZADA

## Implementação - Coluna Tenant

### Base Model com Tenant
```python
# models/base.py

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class TenantMixin:
    """
    Mixin para adicionar tenant_id em TODAS as tabelas
    CRÍTICO para isolamento multi-tenant
    """
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)
    
    @declared_attr
    def tenant(cls):
        return relationship("Tenant")

class TimestampMixin:
    """Campos de auditoria temporal"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class AuditMixin:
    """Campos de auditoria de usuário"""
    created_by = Column(Integer, ForeignKey('usuarios.id'))
    updated_by = Column(Integer, ForeignKey('usuarios.id'))
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
```

### Tenant Model
```python
# models/tenant.py

from sqlalchemy import Column, Integer, String, Boolean, Date, Numeric
from .base import Base, TimestampMixin

class Tenant(Base, TimestampMixin):
    """
    Representa uma empresa cliente do SaaS
    """
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identificação
    nome_empresa = Column(String(200), nullable=False)
    razao_social = Column(String(200), nullable=False)
    cnpj = Column(String(14), unique=True, nullable=False, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)  # URL-friendly
    
    # Status
    ativo = Column(Boolean, default=True, nullable=False)
    plano = Column(String(20), default='trial')  # trial, basic, pro, enterprise
    data_expiracao = Column(Date, nullable=True)
    
    # Limites por plano
    max_usuarios = Column(Integer, default=5)
    max_produtos = Column(Integer, default=1000)
    max_fornecedores = Column(Integer, default=100)
    
    # Configurações de IA
    ia_habilitada = Column(Boolean, default=True)
    ia_auto_aprovacao = Column(Boolean, default=False)
    ia_limite_auto_aprovacao = Column(Numeric(10, 2), default=2000.00)
    
    # IMPORTANTE: Opt-in para compartilhar dados agregados
    compartilhar_dados_agregados = Column(Boolean, default=True)
    
    # Contato
    email_contato = Column(String(200), nullable=False)
    telefone = Column(String(20))
```

### Middleware de Tenant
```python
# middleware/tenant_middleware.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_access_token

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware que identifica o tenant em TODAS as requisições
    e configura o contexto para isolamento de dados
    """
    
    async def dispatch(self, request: Request, call_next):
        # Rotas públicas (sem tenant)
        if request.url.path in ['/api/v1/auth/login', '/docs', '/openapi.json']:
            return await call_next(request)
        
        # Extrair token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token não fornecido")
        
        token = auth_header.replace("Bearer ", "")
        
        try:
            # Decodificar JWT e extrair tenant_id
            payload = decode_access_token(token)
            tenant_id = payload.get("tenant_id")
            
            if not tenant_id:
                raise HTTPException(status_code=401, detail="Tenant não identificado")
            
            # Adicionar ao contexto da request
            request.state.tenant_id = tenant_id
            request.state.user_id = payload.get("user_id")
            
        except Exception as e:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        response = await call_next(request)
        return response
```

### Dependency para Injetar Tenant
```python
# api/deps.py

from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.tenant import Tenant

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_tenant_id(request: Request) -> int:
    """Extrai tenant_id do contexto da request"""
    if not hasattr(request.state, 'tenant_id'):
        raise HTTPException(status_code=400, detail="Tenant não identificado")
    return request.state.tenant_id

def get_current_tenant(
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> Tenant:
    """Retorna objeto Tenant completo"""
    tenant = db.query(Tenant).filter_by(id=tenant_id, ativo=True).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa não encontrada ou inativa")
    return tenant

def get_db_with_tenant_filter(
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> Session:
    """
    Retorna session com Row Level Security configurado
    TODAS as queries filtram automaticamente por tenant_id
    """
    # Configurar RLS do PostgreSQL
    db.execute(f"SET app.current_tenant = {tenant_id}")
    return db
```

---

# AGENTE IA COM INTELIGÊNCIA COLETIVA

## Tabelas de Conhecimento da IA

### Knowledge Base (Compartilhado e Anonimizado)
```python
# models/ia_knowledge.py

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Text
from .base import Base
from datetime import datetime

class IAKnowledgeBase(Base):
    """
    Base de conhecimento AGREGADO e ANONIMIZADO
    NÃO TEM tenant_id - é compartilhado entre todos
    
    Armazena médias de preços, performance de fornecedores, etc
    de forma que é impossível identificar qual tenant forneceu o dado
    """
    __tablename__ = "ia_knowledge_base"
    
    id = Column(Integer, primary_key=True)
    
    tipo_conhecimento = Column(String(50), nullable=False, index=True)
    # Tipos: 'preco_fornecedor', 'performance_fornecedor', 'prazo_entrega'
    
    # Fornecedor (público - CNPJ pode ser público)
    fornecedor_cnpj = Column(String(14), index=True)
    fornecedor_nome = Column(String(200))
    
    # Produto (categoria genérica)
    categoria_produto = Column(String(100), index=True)
    subcategoria_produto = Column(String(100))
    
    # Dados agregados (SEM identificar tenant)
    preco_medio = Column(Numeric(10, 2))
    preco_minimo = Column(Numeric(10, 2))
    preco_maximo = Column(Numeric(10, 2))
    desvio_padrao = Column(Numeric(10, 2))
    qtd_amostras = Column(Integer)  # Número de cotações que geraram essa média
    
    # Performance agregada
    pontualidade_media = Column(Numeric(3, 2))  # 0.00 a 1.00 (0% a 100%)
    qualidade_media = Column(Numeric(3, 2))
    
    # Temporal
    periodo_inicio = Column(Date)
    periodo_fim = Column(Date)
    ultima_atualizacao = Column(DateTime, default=datetime.utcnow)
    
    # Geolocalização (opcional)
    regiao = Column(String(50))  # SE, SUL, NORTE, etc
    
    # NUNCA armazena:
    # - tenant_id (qual empresa)
    # - valores individuais de cotações específicas
    # - datas exatas de transações individuais


class IACotacaoLog(Base):
    """
    Log DETALHADO de cotações - COM tenant_id (PRIVADO)
    Usado para análise específica de cada tenant
    e para gerar dados agregados
    """
    __tablename__ = "ia_cotacao_log"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)
    
    cotacao_id = Column(Integer, ForeignKey('cotacoes.id'))
    fornecedor_id = Column(Integer, ForeignKey('fornecedores.id'))
    produto_id = Column(Integer, ForeignKey('produtos.id'))
    
    preco_cotado = Column(Numeric(10, 2))
    preco_medio_mercado = Column(Numeric(10, 2))  # Do knowledge base na época
    desvio_percentual = Column(Numeric(5, 2))  # -15.00 ou +20.00
    
    foi_escolhido = Column(Boolean, default=False)
    motivo_escolha = Column(Text)
    
    # Feedback (atualizado posteriormente)
    ordem_compra_gerada = Column(Boolean, default=False)
    entrega_pontual = Column(Boolean, nullable=True)
    qualidade_conforme = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

## Serviço de Agregação de Conhecimento
```python
# services/ia_agregacao_service.py

from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.ia_knowledge import IAKnowledgeBase, IACotacaoLog
from app.models.cotacao import Cotacao
from app.models.fornecedor import Fornecedor
from app.models.produto import Produto
from app.models.tenant import Tenant

class IAAgregacaoService:
    """
    Serviço que agrega dados de todos os tenants
    em conhecimento anonimizado
    
    Executado por job agendado (diariamente)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def executar_agregacao_diaria(self):
        """
        Método principal - agrega dados dos últimos 90 dias
        """
        print(f"[{datetime.now()}] Iniciando agregação de conhecimento IA...")
        
        data_inicio = datetime.now() - timedelta(days=90)
        
        # 1. Agregar preços por fornecedor/categoria
        registros_preco = self.agregar_precos_fornecedores(data_inicio)
        print(f"  → Agregados {registros_preco} registros de preços")
        
        # 2. Agregar performance de fornecedores
        registros_perf = self.agregar_performance_fornecedores(data_inicio)
        print(f"  → Agregados {registros_perf} registros de performance")
        
        # 3. Limpar dados antigos (>365 dias)
        removidos = self.limpar_dados_antigos()
        print(f"  → Removidos {removidos} registros antigos")
        
        print(f"[{datetime.now()}] Agregação concluída!")
    
    def agregar_precos_fornecedores(self, data_inicio: datetime) -> int:
        """
        Agrega preços de forma anonimizada
        Considera APENAS tenants que autorizaram compartilhamento
        """
        
        # Query que junta dados de TODOS os tenants autorizados
        query = self.db.query(
            Fornecedor.cnpj.label('fornecedor_cnpj'),
            Fornecedor.razao_social.label('fornecedor_nome'),
            Produto.categoria.label('categoria'),
            Produto.subcategoria.label('subcategoria'),
            func.avg(Cotacao.preco_unitario).label('preco_medio'),
            func.min(Cotacao.preco_unitario).label('preco_minimo'),
            func.max(Cotacao.preco_unitario).label('preco_maximo'),
            func.stddev(Cotacao.preco_unitario).label('desvio_padrao'),
            func.count(Cotacao.id).label('qtd_amostras'),
            func.min(Cotacao.created_at).label('periodo_inicio'),
            func.max(Cotacao.created_at).label('periodo_fim')
        ).join(
            Fornecedor, Cotacao.fornecedor_id == Fornecedor.id
        ).join(
            Produto, Cotacao.produto_id == Produto.id
        ).join(
            Tenant, Cotacao.tenant_id == Tenant.id
        ).filter(
            and_(
                Tenant.compartilhar_dados_agregados == True,
                Cotacao.created_at >= data_inicio
            )
        ).group_by(
            Fornecedor.cnpj,
            Fornecedor.razao_social,
            Produto.categoria,
            Produto.subcategoria
        ).having(
            func.count(Cotacao.id) >= 3  # Mínimo 3 amostras para privacidade
        )
        
        resultados = query.all()
        count = 0
        
        for row in resultados:
            # Upsert no knowledge base
            conhecimento = self.db.query(IAKnowledgeBase).filter_by(
                tipo_conhecimento='preco_fornecedor',
                fornecedor_cnpj=row.fornecedor_cnpj,
                categoria_produto=row.categoria,
                subcategoria_produto=row.subcategoria
            ).first()
            
            if conhecimento:
                # Atualizar existente
                conhecimento.preco_medio = row.preco_medio
                conhecimento.preco_minimo = row.preco_minimo
                conhecimento.preco_maximo = row.preco_maximo
                conhecimento.desvio_padrao = row.desvio_padrao
                conhecimento.qtd_amostras = row.qtd_amostras
                conhecimento.periodo_inicio = row.periodo_inicio
                conhecimento.periodo_fim = row.periodo_fim
                conhecimento.ultima_atualizacao = datetime.now()
            else:
                # Criar novo
                conhecimento = IAKnowledgeBase(
                    tipo_conhecimento='preco_fornecedor',
                    fornecedor_cnpj=row.fornecedor_cnpj,
                    fornecedor_nome=row.fornecedor_nome,
                    categoria_produto=row.categoria,
                    subcategoria_produto=row.subcategoria,
                    preco_medio=row.preco_medio,
                    preco_minimo=row.preco_minimo,
                    preco_maximo=row.preco_maximo,
                    desvio_padrao=row.desvio_padrao,
                    qtd_amostras=row.qtd_amostras,
                    periodo_inicio=row.periodo_inicio,
                    periodo_fim=row.periodo_fim
                )
                self.db.add(conhecimento)
            
            count += 1
        
        self.db.commit()
        return count
    
    def agregar_performance_fornecedores(self, data_inicio: datetime) -> int:
        """
        Agrega performance (pontualidade, qualidade)
        """
        # Implementação similar à de preços
        # Agrega dados de ia_cotacao_log onde tem feedback
        pass
    
    def limpar_dados_antigos(self) -> int:
        """
        Remove registros com mais de 365 dias
        """
        data_limite = datetime.now() - timedelta(days=365)
        
        deleted = self.db.query(IAKnowledgeBase).filter(
            IAKnowledgeBase.periodo_fim < data_limite
        ).delete()
        
        self.db.commit()
        return deleted
```

## Agente IA - Análise de Cotações
```python
# services/ia_agente_service.py

from anthropic import Anthropic
import os
import json
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.cotacao import Cotacao
from app.models.fornecedor import Fornecedor
from app.models.ia_knowledge import IAKnowledgeBase

class IAAgenteService:
    """
    Agente IA que analisa cotações usando:
    1. Dados históricos do próprio tenant
    2. Benchmarks agregados do mercado (todos os tenants)
    
    SEMPRE mantém privacidade - nunca revela dados de outros tenants
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.claude = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    def analisar_cotacoes(
        self,
        tenant_id: int,
        solicitacao_cotacao_id: int
    ) -> Dict:
        """
        Método principal de análise
        """
        # 1. Buscar cotações da solicitação
        cotacoes = self.db.query(Cotacao).filter_by(
            tenant_id=tenant_id,
            solicitacao_id=solicitacao_cotacao_id
        ).all()
        
        if len(cotacoes) < 2:
            return {
                "erro": "Necessário pelo menos 2 cotações para análise",
                "sugestao": None
            }
        
        # 2. Buscar histórico DESTE tenant com os fornecedores
        historico_tenant = self._get_historico_tenant(tenant_id, cotacoes)
        
        # 3. Buscar benchmarks AGREGADOS do mercado
        benchmarks_mercado = self._get_benchmarks_mercado(cotacoes)
        
        # 4. Montar prompt para Claude
        prompt = self._montar_prompt_analise(
            cotacoes,
            historico_tenant,
            benchmarks_mercado
        )
        
        # 5. Chamar Claude API
        response = self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.3,  # Mais determinístico para decisões financeiras
            messages=[{"role": "user", "content": prompt}]
        )
        
        # 6. Parsear resposta
        resultado = json.loads(response.content[0].text)
        
        # 7. Registrar análise no log
        self._registrar_analise(tenant_id, solicitacao_cotacao_id, resultado)
        
        return resultado
    
    def _get_historico_tenant(self, tenant_id: int, cotacoes: List[Cotacao]) -> List[Dict]:
        """
        Busca histórico APENAS deste tenant com os fornecedores cotados
        """
        fornecedor_ids = [c.fornecedor_id for c in cotacoes]
        
        # Buscar últimas 10 compras de cada fornecedor
        historico = []
        
        for fornecedor_id in fornecedor_ids:
            ocs = self.db.query(OrdemCompra).filter_by(
                tenant_id=tenant_id,
                fornecedor_id=fornecedor_id
            ).order_by(OrdemCompra.created_at.desc()).limit(10).all()
            
            if ocs:
                historico.append({
                    "fornecedor_id": fornecedor_id,
                    "total_compras": len(ocs),
                    "entregas_pontuais": sum(1 for oc in ocs if oc.entrega_pontual),
                    "produtos_conformes": sum(1 for oc in ocs if oc.qualidade_conforme),
                    "valor_medio": sum(oc.valor_total for oc in ocs) / len(ocs)
                })
        
        return historico
    
    def _get_benchmarks_mercado(self, cotacoes: List[Cotacao]) -> List[Dict]:
        """
        Busca benchmarks AGREGADOS do mercado
        SEM identificar de quais tenants vieram
        """
        benchmarks = []
        
        for cotacao in cotacoes:
            # Buscar conhecimento agregado
            conhecimento = self.db.query(IAKnowledgeBase).filter_by(
                tipo_conhecimento='preco_fornecedor',
                fornecedor_cnpj=cotacao.fornecedor.cnpj,
                categoria_produto=cotacao.produto.categoria,
                subcategoria_produto=cotacao.produto.subcategoria
            ).first()
            
            if conhecimento and conhecimento.qtd_amostras >= 3:
                desvio = self._calcular_desvio(
                    float(cotacao.preco_unitario),
                    float(conhecimento.preco_medio)
                )
                
                benchmarks.append({
                    "fornecedor": cotacao.fornecedor.razao_social,
                    "preco_cotado": float(cotacao.preco_unitario),
                    "benchmark": {
                        "preco_medio_mercado": float(conhecimento.preco_medio),
                        "preco_min_mercado": float(conhecimento.preco_minimo),
                        "preco_max_mercado": float(conhecimento.preco_maximo),
                        "desvio_percentual": desvio,
                        "amostras": conhecimento.qtd_amostras,
                        "data_atualizacao": conhecimento.ultima_atualizacao.isoformat()
                    }
                })
        
        return benchmarks
    
    def _montar_prompt_analise(
        self,
        cotacoes: List[Cotacao],
        historico: List[Dict],
        benchmarks: List[Dict]
    ) -> str:
        """
        Monta prompt para Claude com INSTRUÇÕES DE PRIVACIDADE
        """
        
        # Serializar cotações
        cotacoes_data = []
        for c in cotacoes:
            cotacoes_data.append({
                "fornecedor": c.fornecedor.razao_social,
                "fornecedor_id": c.fornecedor_id,
                "produto": c.produto.descricao,
                "preco_unitario": float(c.preco_unitario),
                "quantidade": float(c.quantidade),
                "prazo_dias": c.prazo_entrega,
                "frete": float(c.frete) if c.frete else 0,
                "total": float(c.preco_unitario * c.quantidade + (c.frete or 0))
            })
        
        prompt = f"""
Você é um especialista em análise de compras para indústrias de mármore e granito.

COTAÇÕES RECEBIDAS:
{json.dumps(cotacoes_data, indent=2, ensure_ascii=False)}

HISTÓRICO COM ESTES FORNECEDORES (desta empresa):
{json.dumps(historico, indent=2, ensure_ascii=False)}

BENCHMARKS DE MERCADO (dados agregados e anonimizados):
{json.dumps(benchmarks, indent=2, ensure_ascii=False)}

INSTRUÇÕES CRÍTICAS SOBRE PRIVACIDADE:
1. Os benchmarks de mercado são MÉDIAS de múltiplas empresas do setor
2. São baseados em {sum(b['benchmark'].get('amostras', 0) for b in benchmarks)} cotações reais agregadas
3. NUNCA mencione que são de "outras empresas" ou "outros clientes"
4. Use APENAS expressões como:
   ✅ "Preço está 15% acima da média de mercado"
   ✅ "Dentro da faixa normal para este tipo de produto"
   ✅ "Preço competitivo comparado aos benchmarks do setor"
   ✅ "Dados de mercado indicam que este é um bom preço"
5. NUNCA use:
   ❌ "Outra empresa conseguiu X"
   ❌ "Cliente Y pagou menos"
   ❌ "Comparado com outras compras"

CRITÉRIOS DE ANÁLISE (pesos):
- Custo total (preço + frete): 35%
- Prazo de entrega: 25%
- Histórico de pontualidade: 20%
- Histórico de qualidade: 15%
- Desvio vs mercado: 5%

ANÁLISE SOLICITADA:
1. Compare as cotações entre si
2. Considere o histórico desta empresa com cada fornecedor
3. Compare com benchmarks de mercado (quando disponíveis)
4. Identifique desvios significativos (>15% da média)
5. Sugira o melhor fornecedor

RESPONDA APENAS COM JSON VÁLIDO:
{{
  "fornecedor_recomendado": "Nome do fornecedor",
  "fornecedor_id": 123,
  "score_final": 8.5,
  "ranking": [
    {{
      "fornecedor": "Nome",
      "score": 8.5,
      "pontos_positivos": ["item 1", "item 2"],
      "pontos_negativos": ["item 1"]
    }}
  ],
  "justificativa": "Análise detalhada em 3-4 parágrafos explicando a escolha, considerando todos os critérios. Mencione benchmarks de mercado quando relevante, mas SEMPRE de forma agregada.",
  "alertas": ["Pontos de atenção, se houver"],
  "economia_vs_mais_caro": 1500.00,
  "custo_extra_vs_mais_barato": 200.00,
  "analise_mercado": {{
    "disponivel": true/false,
    "resumo": "Breve análise dos preços vs mercado"
  }}
}}
"""
        return prompt
    
    def _calcular_desvio(self, valor: float, referencia: float) -> float:
        """Calcula desvio percentual"""
        if referencia == 0:
            return 0
        return round(((valor - referencia) / referencia) * 100, 2)
    
    def _registrar_analise(self, tenant_id: int, solicitacao_id: int, resultado: Dict):
        """Registra análise no banco para feedback futuro"""
        # Implementar registro em tabela de logs
        pass
```

## Job Agendado de Agregação
```python
# jobs/agregacao_ia.py

from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.ia_agregacao_service import IAAgregacaoService

def job_agregacao_diaria():
    """
    Job que roda diariamente às 01:00 AM
    Agrega conhecimento de todos os tenants
    """
    db = SessionLocal()
    try:
        servico = IAAgregacaoService(db)
        servico.executar_agregacao_diaria()
    except Exception as e:
        print(f"Erro no job de agregação: {e}")
    finally:
        db.close()

def iniciar_scheduler():
    """
    Inicia o scheduler de jobs
    Chamado no main.py durante startup da aplicação
    """
    scheduler = BackgroundScheduler()
    
    # Job de agregação diária às 01:00
    scheduler.add_job(
        job_agregacao_diaria,
        'cron',
        hour=1,
        minute=0,
        id='agregacao_ia'
    )
    
    scheduler.start()
    print("✓ Scheduler de jobs iniciado")
```

---

# MÓDULOS E FUNCIONALIDADES

[NOTA: Aqui você incluiria TODAS as funcionalidades detalhadas do prompt anterior:
- Gestão de Produtos
- Gestão de Fornecedores
- Processo de Cotação
- Processo de Compra
- Recebimento e Estoque
- Relatórios e Dashboards

Por questão de espaço, vou resumir os principais pontos, mas você deve incluir TUDO do prompt anterior]

## Resumo dos Módulos:

1. **Cadastros Base**: Produtos, Fornecedores, Categorias
2. **Cotações**: Solicitação, recebimento, análise com IA
3. **Compras**: Requisição, aprovação workflow, ordem de compra
4. **Estoque**: Movimentações, inventário, alertas
5. **IA**: Análise automática, benchmarks, sugestões
6. **Relatórios**: Dashboard, gerenciais, operacionais

---

# FASES DE IMPLEMENTAÇÃO

## FASE 0: SETUP INICIAL (COMECE AQUI!) ⚡

### 0.1 Criar Conta Railway
1. Acessar https://railway.app
2. Criar conta (pode usar GitHub)
3. Criar novo projeto
4. Adicionar PostgreSQL
5. Copiar `DATABASE_URL` (Connection String)

### 0.2 Estrutura de Pastas
```bash
mkdir sistema-compras-saas
cd sistema-compras-saas
mkdir backend frontend
```

### 0.3 Backend Inicial
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# Windows: venv\Scripts\activate

# Criar requirements.txt com as dependências listadas acima
pip install -r requirements.txt

# Criar estrutura de pastas
mkdir -p app/{core,middleware,models,schemas,api/routes,services,jobs,utils}
mkdir alembic tests
```

### 0.4 Arquivos de Configuração Base

**backend/.env**
```env
DATABASE_URL=postgresql://...  # Do Railway
SECRET_KEY=gerar-chave-forte-aqui
ANTHROPIC_API_KEY=sua-chave-aqui
```

**backend/app/config.py**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ANTHROPIC_API_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**backend/app/database.py**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**backend/app/main.py**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.tenant_middleware import TenantMiddleware
from app.api.routes import auth, tenants, produtos
# ... outros imports

app = FastAPI(title="Sistema de Compras Multi-Tenant")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant Middleware
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
app.include_router(produtos.router, prefix="/api/v1/produtos", tags=["produtos"])

@app.get("/")
def root():
    return {"message": "Sistema de Compras Multi-Tenant API"}

# Iniciar scheduler de jobs no startup
@app.on_event("startup")
def startup_event():
    from app.jobs.agregacao_ia import iniciar_scheduler
    iniciar_scheduler()
```

### 0.5 Frontend Inicial
```bash
cd ../frontend
npm create vite@latest . -- --template react-ts
npm install
npm install @tanstack/react-query axios react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Instalar shadcn/ui
npx shadcn-ui@latest init
```

### 0.6 Alembic Setup
```bash
cd ../backend
alembic init alembic

# Editar alembic.ini:
# sqlalchemy.url = postgresql://...

# Editar alembic/env.py para importar Base
```

**ENTREGA FASE 0:**
- ✅ Railway PostgreSQL configurado
- ✅ Backend rodando (uvicorn app.main:app --reload)
- ✅ Frontend rodando (npm run dev)
- ✅ Alembic configurado

---

## FASE 1: AUTENTICAÇÃO E MULTI-TENANCY (1 semana)

### 1.1 Models Base
- Criar `models/base.py` com mixins
- Criar `models/tenant.py`
- Criar `models/usuario.py`

### 1.2 Autenticação
- JWT com tenant_id no payload
- Rotas de login/registro
- Middleware de tenant

### 1.3 Frontend Auth
- Context de autenticação
- Tela de login
- Rotas protegidas

**ENTREGA FASE 1:**
- Login funcionando
- Tenant isolado
- Testes com 2 empresas diferentes

---

## FASE 2: CADASTROS BASE (2 semanas)

### 2.1 Produtos
- Model + Schema + Routes
- CRUD completo
- Upload de imagem
- Testes

### 2.2 Fornecedores
- Model + Schema + Routes
- CRUD completo
- Múltiplos contatos

### 2.3 Frontend
- Listagens com filtros
- Formulários com validação
- Upload de arquivos

**ENTREGA FASE 2:**
- Cadastros funcionando
- Dados isolados por tenant

---

## FASE 3: COTAÇÕES (2 semanas)

### 3.1 Processo de Cotação
- Solicitação
- Registro de propostas
- Mapa comparativo

### 3.2 IA - Primeira Versão
- Análise básica (sem benchmarks ainda)
- Sugestão de fornecedor

**ENTREGA FASE 3:**
- Cotações funcionando
- IA sugerindo fornecedor

---

## FASE 4: INTELIGÊNCIA COLETIVA (2 semanas)

### 4.1 Knowledge Base
- Tabelas de conhecimento
- Job de agregação
- Opt-in de compartilhamento

### 4.2 IA Completa
- Benchmarks de mercado
- Análise com conhecimento coletivo
- Privacidade garantida

**ENTREGA FASE 4:**
- IA usando dados agregados
- Dashboard de benchmarks

---

## FASE 5: COMPRAS E ESTOQUE (3 semanas)

### 5.1 Requisição e Aprovação
- Workflow configurável
- Notificações

### 5.2 Ordem de Compra
- Geração de OC
- Acompanhamento

### 5.3 Estoque
- Movimentações
- Inventário
- Alertas

**ENTREGA FASE 5:**
- Fluxo completo funcionando
- Estoque rastreável

---

## FASE 6: RELATÓRIOS E POLIMENTO (2 semanas)

### 6.1 Dashboard
- KPIs principais
- Gráficos interativos

### 6.2 Relatórios
- Gerenciais
- Operacionais
- Exportação

### 6.3 Testes e Deploy
- Testes E2E
- Deploy Railway
- Documentação

**ENTREGA FINAL:**
- Sistema completo
- Documentado
- Em produção

---

# BOAS PRÁTICAS OBRIGATÓRIAS

## Segurança Multi-Tenant

### NUNCA fazer queries sem tenant_id
```python
# ❌ ERRADO - Vaza dados de outros tenants
produtos = db.query(Produto).all()

# ✅ CORRETO - Sempre filtrar por tenant
produtos = db.query(Produto).filter_by(tenant_id=tenant_id).all()

# ✅ MELHOR - Usar RLS (configurado no middleware)
# Com RLS habilitado, o filtro é automático
produtos = db.query(Produto).all()  # Só retorna do tenant atual
```

### Índices Compostos Obrigatórios
```python
# Em TODAS as tabelas com tenant_id
__table_args__ = (
    Index('idx_produtos_tenant_id', 'tenant_id', 'id'),
    Index('idx_produtos_tenant_codigo', 'tenant_id', 'codigo'),
)
```

### Row Level Security (RLS)
```sql
-- Executar no PostgreSQL para cada tabela

-- Habilitar RLS
ALTER TABLE produtos ENABLE ROW LEVEL SECURITY;

-- Criar política
CREATE POLICY tenant_isolation_policy ON produtos
    USING (tenant_id = current_setting('app.current_tenant')::integer);

-- Aplicar em todas as tabelas com tenant_id
```

## IA - Privacidade

### NUNCA agregar com menos de 3 amostras
```python
# Garante que é impossível identificar origem
HAVING COUNT(*) >= 3
```

### SEMPRE verificar opt-in
```python
WHERE tenant.compartilhar_dados_agregados = true
```

### NUNCA mencionar "outras empresas"
```python
# ✅ BOM
"Preço está 15% acima da média de mercado"

# ❌ RUIM
"Outra empresa conseguiu 10% mais barato"
```

---

# CHECKLIST ANTES DE COMEÇAR

- [ ] Conta Railway criada e PostgreSQL provisionado
- [ ] DATABASE_URL copiada
- [ ] Python 3.11+ instalado
- [ ] Node.js 18+ instalado
- [ ] Anthropic API Key obtida (https://console.anthropic.com)
- [ ] Git instalado e configurado
- [ ] VSCode com extensões (Python, ESLint, Tailwind)

---

# COMECE AGORA!

**Sua primeira tarefa é FASE 0:**

1. Configurar Railway
2. Criar estrutura de pastas
3. Instalar dependências backend
4. Criar arquivos config, database, main
5. Configurar frontend básico
6. Testar conexão com banco

**Após concluir Fase 0, me avise e eu valido antes de prosseguir para Fase 1.**

Cada fase deve incluir:
- ✅ Código funcionando
- ✅ Migrations aplicadas
- ✅ Testes básicos
- ✅ README atualizado

**Perguntas? Dúvidas? Pode perguntar antes de implementar!**

**BOA SORTE E MÃOS À OBRA! 🚀**