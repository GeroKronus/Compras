# Sistema de Gestão de Compras Multi-Tenant com IA

Sistema SaaS para gestão de compras e estoque com inteligência artificial, desenvolvido para empresas do setor de mineração e beneficiamento de rochas ornamentais.

## Características

- **Multi-Tenant**: Múltiplas empresas usando a mesma infraestrutura com isolamento total de dados
- **Agente IA**: Análise automática de cotações usando Claude (Anthropic)
- **Inteligência Coletiva**: Benchmarks agregados e anonimizados de todas as empresas
- **Privacidade por Design**: Dados isolados por empresa, conhecimento compartilhado de forma anônima

## Stack Tecnológica

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL 15
- SQLAlchemy 2.0
- Alembic (migrations)
- JWT Authentication
- Anthropic Claude API

### Frontend
- React 18 + TypeScript
- Vite
- TanStack Query (React Query)
- Tailwind CSS
- Shadcn/ui
- Axios

## Pré-requisitos

- Python 3.11+
- Node.js 18+
- Docker e Docker Compose
- Git

## Setup Inicial (FASE 0)

### 1. Clonar o repositório
```bash
git clone <seu-repositorio>
cd sistema-compras-saas
```

### 2. Configurar Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Copiar arquivo .env (já configurado com defaults)
# Editar backend/.env se necessário (DATABASE_URL, SECRET_KEY, etc)
```

### 3. Iniciar PostgreSQL (Docker)

```bash
# Na raiz do projeto
docker-compose up -d

# Verificar se está rodando
docker ps
```

### 4. Criar Migration e Tabelas

```bash
cd backend

# Gerar primeira migration
alembic revision --autogenerate -m "Initial tables: tenants and usuarios"

# Aplicar migration
alembic upgrade head
```

### 5. Iniciar Backend

```bash
# Na pasta backend
uvicorn app.main:app --reload

# API estará disponível em:
# http://localhost:8000
# Documentação: http://localhost:8000/docs
```

### 6. Configurar Frontend

```bash
cd frontend

# Instalar dependências
npm install

# O arquivo .env já está configurado com:
# VITE_API_URL=http://localhost:8000/api/v1

# Iniciar servidor de desenvolvimento
npm run dev

# Frontend estará disponível em:
# http://localhost:5173
```

## Testando o Sistema

### 1. Criar Primeiro Tenant (Empresa)

Use a API em http://localhost:8000/docs ou faça uma requisição:

```bash
curl -X POST "http://localhost:8000/api/v1/tenants/register" \
  -H "Content-Type: application/json" \
  -d '{
    "nome_empresa": "Mármores ABC Ltda",
    "razao_social": "Mármores ABC Indústria e Comércio Ltda",
    "cnpj": "12345678000190",
    "email_contato": "contato@marmoresabc.com",
    "telefone": "27999999999",
    "plano": "trial",
    "admin_nome": "João Silva",
    "admin_email": "joao@marmoresabc.com",
    "admin_senha": "Senha123"
  }'
```

### 2. Fazer Login

Acesse http://localhost:5173/login e entre com:
- CNPJ: `12345678000190`
- Email: `joao@marmoresabc.com`
- Senha: `Senha123`

### 3. Explorar Dashboard

Após o login, você verá o dashboard inicial com informações da empresa.

## Estrutura do Projeto

```
sistema-compras-saas/
├── backend/
│   ├── app/
│   │   ├── core/              # Segurança e contexto
│   │   ├── middleware/        # Middleware de tenant
│   │   ├── models/            # Models SQLAlchemy
│   │   ├── schemas/           # Schemas Pydantic
│   │   ├── api/               # Rotas da API
│   │   ├── services/          # Lógica de negócio
│   │   └── ...
│   ├── alembic/               # Migrations
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/        # Componentes React
│   │   ├── pages/             # Páginas
│   │   ├── services/          # API services
│   │   ├── hooks/             # Custom hooks
│   │   └── types/             # TypeScript types
│   └── package.json
│
├── docker-compose.yml         # PostgreSQL
└── README.md
```

## Comandos Úteis

### Backend
```bash
# Criar nova migration
alembic revision --autogenerate -m "Descrição"

# Aplicar migrations
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# Ver histórico de migrations
alembic history

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
# Desenvolvimento
npm run dev

# Build para produção
npm run build

# Preview do build
npm run preview
```

### Docker
```bash
# Iniciar PostgreSQL
docker-compose up -d

# Parar PostgreSQL
docker-compose down

# Ver logs
docker-compose logs -f

# Resetar banco (CUIDADO!)
docker-compose down -v
```

## Próximas Fases

### FASE 1: Autenticação e Multi-Tenancy (1 semana)
- [ ] Testes de isolamento multi-tenant
- [ ] Refresh token
- [ ] Recuperação de senha
- [ ] Gestão de usuários

### FASE 2: Cadastros Base (2 semanas)
- [ ] CRUD de Produtos
- [ ] CRUD de Fornecedores
- [ ] Categorias e Subcategorias
- [ ] Upload de arquivos

### FASE 3: Cotações (2 semanas)
- [ ] Solicitação de cotação
- [ ] Registro de propostas
- [ ] Mapa comparativo
- [ ] IA - análise básica

### FASE 4: Inteligência Coletiva (2 semanas)
- [ ] Knowledge Base agregado
- [ ] Job de agregação
- [ ] IA com benchmarks de mercado
- [ ] Dashboard de inteligência

### FASE 5: Compras e Estoque (3 semanas)
- [ ] Requisição de compra
- [ ] Workflow de aprovação
- [ ] Ordem de compra
- [ ] Gestão de estoque
- [ ] Alertas

### FASE 6: Relatórios e Deploy (2 semanas)
- [ ] Dashboard completo
- [ ] Relatórios gerenciais
- [ ] Exportação de dados
- [ ] Deploy em produção
- [ ] Documentação final

## Status Atual

✅ **FASE 0 - SETUP INICIAL COMPLETO**

- Backend FastAPI configurado
- PostgreSQL rodando no Docker
- Models e Migrations criados
- Sistema de autenticação JWT
- Middleware Multi-Tenant
- Frontend React + TypeScript
- Tailwind CSS + Shadcn/ui
- Integração Backend ↔ Frontend

## Contribuindo

Este é um projeto em desenvolvimento ativo. Contribuições são bem-vindas!

## Licença

[Definir licença]

## Suporte

Para dúvidas e suporte, abra uma issue no repositório.
