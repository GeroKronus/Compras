# Deploy no Railway - Sistema de Compras Multi-Tenant

## Visão Geral da Arquitetura

O projeto é composto por 3 serviços no Railway:
1. **Backend** (FastAPI/Python)
2. **Frontend** (React/Vite)
3. **Postgres** (Banco de dados)

---

## Passo 1: Criar Projeto no Railway

1. Acesse [railway.app](https://railway.app)
2. Faça login com GitHub
3. Clique em "New Project"

---

## Passo 2: Criar Banco de Dados PostgreSQL

1. No projeto, clique em "Add Service" → "Database" → "PostgreSQL"
2. O Railway criará automaticamente o banco
3. Clique no serviço Postgres para ver as credenciais
4. Anote a variável `DATABASE_URL` (será usada no backend)

---

## Passo 3: Deploy do Backend

### 3.1 Adicionar o Serviço
1. Clique em "Add Service" → "GitHub Repo"
2. Selecione o repositório do projeto
3. **IMPORTANTE:** Configure o Root Directory como `backend`

### 3.2 Configurar Variáveis de Ambiente
No painel do serviço backend, vá em "Variables" e adicione:

```
# Database - Referência ao serviço Postgres
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Segurança (GERE UMA CHAVE SEGURA!)
SECRET_KEY=sua-chave-segura-com-pelo-menos-64-caracteres-aleatorios-aqui-12345

# Ambiente
ENVIRONMENT=production
API_V1_STR=/api/v1
PROJECT_NAME=Sistema de Compras Multi-Tenant

# CORS - URL do frontend (será definida após deploy do frontend)
BACKEND_CORS_ORIGINS=https://seu-frontend.railway.app

# Anthropic AI
ANTHROPIC_API_KEY=sk-ant-xxxx

# Email (Zoho)
SMTP_HOST=smtppro.zoho.com
SMTP_PORT=465
SMTP_USER=seu-email@empresa.com
SMTP_PASSWORD=sua-senha-app
EMAIL_FROM=seu-email@empresa.com
IMAP_HOST=imappro.zoho.com
IMAP_PORT=993

# Jobs agendados
ENABLE_SCHEDULED_JOBS=true
```

### 3.3 Gerar uma SECRET_KEY segura
Execute este comando Python para gerar:
```python
import secrets
print(secrets.token_hex(32))
```

### 3.4 Deploy
1. O Railway detectará automaticamente o `railway.toml` e fará o build
2. Aguarde o deploy completar
3. Anote a URL do backend (ex: `https://backend-xxx.railway.app`)

---

## Passo 4: Inicializar o Banco de Dados

### 4.1 Rodar Migrações
No terminal do Railway (ou conectando via CLI):

```bash
# Conectar ao serviço backend
railway run alembic upgrade head
```

Ou use o terminal web do Railway no serviço backend.

### 4.2 Criar Tabelas (alternativa manual)
Se não usar Alembic, as tabelas são criadas automaticamente no startup se usar:
```python
Base.metadata.create_all(bind=engine)
```

---

## Passo 5: Deploy do Frontend

### 5.1 Adicionar o Serviço
1. Clique em "Add Service" → "GitHub Repo"
2. Selecione o mesmo repositório
3. **IMPORTANTE:** Configure o Root Directory como `frontend`

### 5.2 Configurar Variáveis de Ambiente
```
VITE_API_URL=https://seu-backend.railway.app/api/v1
```

### 5.3 Configurar Build
- Build Command: `npm run build`
- Start Command: `npm run preview -- --host 0.0.0.0 --port $PORT`

### 5.4 Deploy
1. Aguarde o build completar
2. Anote a URL do frontend

---

## Passo 6: Atualizar CORS no Backend

Após o deploy do frontend, volte ao backend e atualize:

```
BACKEND_CORS_ORIGINS=https://seu-frontend.railway.app
```

Se tiver domínio próprio, adicione também:
```
BACKEND_CORS_ORIGINS=https://seu-frontend.railway.app,https://seu-dominio.com.br
```

---

## Passo 7: Configurar Domínios (Opcional)

### Backend
1. Vá em "Settings" → "Networking" → "Generate Domain"
2. Ou adicione domínio customizado em "Custom Domain"

### Frontend
1. Mesmo processo para o frontend

---

## Variáveis de Ambiente - Resumo

### Backend
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| DATABASE_URL | Conexão PostgreSQL | ${{Postgres.DATABASE_URL}} |
| SECRET_KEY | Chave JWT (64+ chars) | abc123... |
| ENVIRONMENT | Ambiente | production |
| BACKEND_CORS_ORIGINS | URLs permitidas | https://... |
| ANTHROPIC_API_KEY | API Anthropic | sk-ant-... |
| SMTP_HOST | Servidor SMTP | smtppro.zoho.com |
| SMTP_PORT | Porta SMTP | 465 |
| SMTP_USER | Email SMTP | email@empresa.com |
| SMTP_PASSWORD | Senha app | *** |
| EMAIL_FROM | Remetente | email@empresa.com |
| IMAP_HOST | Servidor IMAP | imappro.zoho.com |
| IMAP_PORT | Porta IMAP | 993 |
| ENABLE_SCHEDULED_JOBS | Habilitar jobs | true |

### Frontend
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| VITE_API_URL | URL da API | https://backend.railway.app/api/v1 |

---

## Troubleshooting

### Erro de CORS
- Verifique se `BACKEND_CORS_ORIGINS` inclui a URL do frontend
- Certifique-se de incluir `https://` no início

### Erro de Database
- Verifique se o serviço Postgres está rodando
- Confirme que `DATABASE_URL` usa a referência correta `${{Postgres.DATABASE_URL}}`

### Build falhou
- Verifique os logs de build no Railway
- Confirme que `requirements.txt` está no diretório backend

### Frontend não conecta no backend
- Verifique se `VITE_API_URL` está correto
- Confirme que o backend está healthy (endpoint `/health`)

---

## Criar Usuário MASTER Inicial

Após o deploy, você precisa criar o primeiro usuário MASTER.
Execute no terminal do Railway ou via API:

```sql
-- Via SQL direto no Postgres
INSERT INTO usuarios (tenant_id, nome_completo, email, senha_hash, tipo, ativo, created_at, updated_at)
VALUES (
    1, -- ou o ID do seu tenant
    'Seu Nome',
    'seu-email@empresa.com',
    '$2b$12$...',  -- hash bcrypt da senha
    'MASTER',
    true,
    NOW(),
    NOW()
);
```

Ou crie via script Python rodando no Railway.

---

## Custos Estimados

O Railway oferece $5/mês de crédito no plano gratuito.
Custos típicos:
- PostgreSQL: ~$5/mês
- Backend: ~$5/mês
- Frontend: ~$5/mês

Total: ~$15/mês para ambiente de produção básico.
