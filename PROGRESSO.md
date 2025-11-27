# Sistema de Gestao de Compras - Progresso do Desenvolvimento

## Visao Geral

Sistema multi-tenant para gestao completa do ciclo de compras empresariais.

**Stack Tecnologico:**
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL
- **Frontend:** React 18 + TypeScript + TailwindCSS + TanStack Query
- **Autenticacao:** JWT com suporte multi-tenant

---

## FASES CONCLUIDAS

### FASE 1 - Infraestrutura Base

| Item | Status | Descricao |
|------|--------|-----------|
| Estrutura do projeto | Concluido | Backend e Frontend organizados |
| Configuracao FastAPI | Concluido | CORS, rotas, middlewares |
| Configuracao React | Concluido | Vite, TailwindCSS, React Router |
| Banco de dados | Concluido | PostgreSQL com SQLAlchemy 2.0 |
| Migrations | Concluido | Alembic configurado |
| Autenticacao JWT | Concluido | Login, registro, refresh token |
| Multi-tenancy | Concluido | Isolamento por tenant_id |

**Arquivos principais:**
- `backend/app/main.py` - Aplicacao FastAPI
- `backend/app/core/config.py` - Configuracoes
- `backend/app/core/security.py` - JWT e hash de senhas
- `backend/app/api/deps.py` - Dependencias (get_db, get_current_user)
- `frontend/src/App.tsx` - Rotas React
- `frontend/src/services/api.ts` - Cliente Axios

---

### FASE 2 - Cadastros Basicos

| Modulo | Status | Funcionalidades |
|--------|--------|-----------------|
| Tenants | Concluido | CRUD completo, configuracoes |
| Usuarios | Concluido | CRUD, roles (ADMIN, COMPRADOR, APROVADOR, VISUALIZADOR) |
| Categorias | Concluido | CRUD com hierarquia (categoria pai) |
| Produtos | Concluido | CRUD, estoque, especificacoes JSON |
| Fornecedores | Concluido | CRUD, avaliacao (rating), aprovacao |

**Models:**
- `backend/app/models/tenant.py`
- `backend/app/models/usuario.py`
- `backend/app/models/categoria.py`
- `backend/app/models/produto.py`
- `backend/app/models/fornecedor.py`

**Schemas Pydantic:**
- `backend/app/schemas/` - Todos os schemas de validacao

**Rotas API:**
- `POST/GET/PUT/DELETE /categorias/`
- `POST/GET/PUT/DELETE /produtos/`
- `POST/GET/PUT/DELETE /fornecedores/`
- `PATCH /fornecedores/{id}/aprovar`
- `PATCH /fornecedores/{id}/reprovar`
- `PATCH /fornecedores/{id}/avaliacao`

**Paginas Frontend:**
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Categorias.tsx`
- `frontend/src/pages/Produtos.tsx`
- `frontend/src/pages/Fornecedores.tsx`

---

### FASE 3 - Cotacoes

| Funcionalidade | Status | Descricao |
|----------------|--------|-----------|
| Solicitacao de Cotacao | Concluido | Criar, editar, enviar, cancelar |
| Itens da Solicitacao | Concluido | Produtos com quantidade e especificacoes |
| Propostas de Fornecedores | Concluido | Registrar propostas com precos |
| Itens da Proposta | Concluido | Precos, descontos, prazos por item |
| Mapa Comparativo | Concluido | Comparacao lado a lado |
| Sugestao IA | Concluido | Algoritmo de pontuacao (preco/prazo/condicoes) |
| Escolha de Vencedor | Concluido | Finalizar cotacao |

**Status de Solicitacao:**
- `RASCUNHO` → `ENVIADA` → `EM_COTACAO` → `FINALIZADA`
- `CANCELADA` (qualquer momento)

**Status de Proposta:**
- `PENDENTE` → `RECEBIDA` → `VENCEDORA` ou `REJEITADA`

**Rotas API:**
- `POST/GET/PUT/DELETE /cotacoes/solicitacoes`
- `POST /cotacoes/solicitacoes/{id}/enviar`
- `POST /cotacoes/solicitacoes/{id}/cancelar`
- `POST /cotacoes/solicitacoes/{id}/escolher-vencedor`
- `GET /cotacoes/solicitacoes/{id}/mapa-comparativo`
- `GET /cotacoes/solicitacoes/{id}/sugestao-ia`
- `POST/GET /cotacoes/propostas`
- `GET /cotacoes/solicitacoes/{id}/propostas`

**Paginas Frontend:**
- `frontend/src/pages/Cotacoes.tsx` - Lista de solicitacoes
- `frontend/src/pages/Propostas.tsx` - Registrar propostas
- `frontend/src/pages/MapaComparativo.tsx` - Comparar e escolher vencedor
- `frontend/src/pages/SugestaoIA.tsx` - Recomendacao automatica

---

### FASE 4 - Pedidos de Compra

| Funcionalidade | Status | Descricao |
|----------------|--------|-----------|
| Pedido de Compra | Concluido | CRUD completo |
| Itens do Pedido | Concluido | Produtos, quantidades, precos |
| Workflow de Aprovacao | Concluido | Enviar, aprovar, rejeitar |
| Envio ao Fornecedor | Concluido | Marcar como enviado |
| Confirmacao | Concluido | Fornecedor confirma pedido |
| Gerar de Cotacao | Concluido | Auto-gerar pedido da proposta vencedora |

**Status de Pedido:**
- `RASCUNHO` → `AGUARDANDO_APROVACAO` → `APROVADO` → `ENVIADO_FORNECEDOR` → `CONFIRMADO` → `EM_TRANSITO` → `ENTREGUE`
- `REJEITADO` ou `CANCELADO` (em pontos especificos)

**Rotas API:**
- `POST/GET/PUT/DELETE /pedidos/`
- `POST /pedidos/from-cotacao` - Gerar de cotacao
- `POST /pedidos/{id}/enviar-aprovacao`
- `POST /pedidos/{id}/aprovar`
- `POST /pedidos/{id}/rejeitar`
- `POST /pedidos/{id}/enviar-fornecedor`
- `POST /pedidos/{id}/confirmar`
- `POST /pedidos/{id}/cancelar`
- `POST /pedidos/{id}/registrar-entrega`

**Paginas Frontend:**
- `frontend/src/pages/Pedidos.tsx` - Lista e gestao de pedidos

---

### Refatoracao DRY (Concluida)

| Abstracoes Backend | Arquivo | Funcoes |
|--------------------|---------|---------|
| DB Helpers | `utils/db_helpers.py` | `get_by_id`, `validate_fk`, `validate_unique` |
| Paginacao | `utils/pagination.py` | `paginate_query`, `apply_search_filter` |
| Sequenciais | `utils/sequencers.py` | `generate_sequential_number` |
| Updates | `utils/updates.py` | `update_entity`, `bulk_update` |
| Status | `utils/status.py` | `require_status`, `forbid_status` |

| Abstracoes Frontend | Arquivo | Exports |
|---------------------|---------|---------|
| Formatadores | `utils/formatters.ts` | `formatCurrency`, `formatDate`, `formatCNPJ` |
| Status Config | `utils/statusConfig.ts` | `getStatusColor`, `getStatusLabel`, `getStatusOptions` |
| Layout | `components/PageLayout.tsx` | `PageLayout`, `PageSection` |
| Modais | `components/Modal.tsx` | `Modal`, `ConfirmModal`, `ViewModal` |
| Status Badge | `components/StatusBadge.tsx` | `StatusBadge` |
| Hook Modal | `hooks/useModal.ts` | `useModal`, `useModals` |
| Hook CRUD | `hooks/useCrudResource.ts` | `useCrudResource`, `useCrudItem` |

**Reducao de codigo:**
- `categorias.py`: 187 → 109 linhas (-42%)
- `produtos.py`: 225 → 124 linhas (-45%)
- `fornecedores.py`: 254 → 142 linhas (-44%)
- `cotacoes.py`: 880 → 602 linhas (-32%)
- `Cotacoes.tsx`: 860 → 484 linhas (-44%)

---

## FASES PENDENTES

### FASE 5 - Recebimento e Estoque

| Funcionalidade | Status | Descricao |
|----------------|--------|-----------|
| Recebimento de Mercadorias | Pendente | Registrar chegada de pedidos |
| Conferencia | Pendente | Verificar quantidade x pedido |
| Nota Fiscal | Pendente | Vincular NF ao recebimento |
| Movimentacao de Estoque | Pendente | Entrada automatica no estoque |
| Devolucao | Pendente | Registrar itens devolvidos |
| Historico de Movimentacoes | Pendente | Log de todas as movimentacoes |

**Estrutura sugerida:**
```
Models:
- Recebimento (pedido_id, data, nf_numero, nf_serie, status)
- ItemRecebimento (recebimento_id, item_pedido_id, qtd_recebida, qtd_rejeitada)
- MovimentacaoEstoque (produto_id, tipo, quantidade, referencia)

Status Recebimento:
- PENDENTE → EM_CONFERENCIA → CONCLUIDO
- CONCLUIDO_COM_DIVERGENCIA
```

---

### FASE 6 - Relatorios e Dashboards

| Funcionalidade | Status | Descricao |
|----------------|--------|-----------|
| Dashboard Gerencial | Pendente | KPIs, graficos, resumos |
| Relatorio de Compras | Pendente | Por periodo, fornecedor, categoria |
| Relatorio de Economia | Pendente | Comparativo de precos |
| Relatorio de Fornecedores | Pendente | Performance, ranking |
| Relatorio de Estoque | Pendente | Posicao, giro, ABC |
| Exportacao PDF/Excel | Pendente | Download de relatorios |

**KPIs sugeridos:**
- Total de compras no periodo
- Economia obtida em cotacoes
- Tempo medio de ciclo de compra
- Fornecedores mais utilizados
- Produtos mais comprados
- Pedidos pendentes de aprovacao

---

### FASE 7 - Notificacoes

| Funcionalidade | Status | Descricao |
|----------------|--------|-----------|
| Notificacoes In-App | Pendente | Badge, lista de notificacoes |
| Email Transacional | Pendente | Envio de emails automaticos |
| Alertas de Estoque | Pendente | Estoque minimo atingido |
| Alertas de Aprovacao | Pendente | Pedidos aguardando aprovacao |
| Alertas de Vencimento | Pendente | Propostas/pedidos expirando |

**Eventos para notificar:**
- Nova solicitacao de cotacao
- Proposta recebida
- Pedido aguardando aprovacao
- Pedido aprovado/rejeitado
- Entrega registrada
- Estoque abaixo do minimo

---

### FASE 8 - Integracoes (Opcional)

| Funcionalidade | Status | Descricao |
|----------------|--------|-----------|
| Importacao de Produtos | Pendente | CSV/Excel |
| Importacao de Fornecedores | Pendente | CSV/Excel |
| Integracao ERP | Pendente | API REST para integracao |
| Integracao Contabil | Pendente | Exportar lancamentos |
| Webhook de Eventos | Pendente | Notificar sistemas externos |

---

## Estrutura de Arquivos Atual

```
Gestao de compras/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── categorias.py
│   │   │   │   ├── produtos.py
│   │   │   │   ├── fornecedores.py
│   │   │   │   ├── cotacoes.py
│   │   │   │   └── pedidos.py
│   │   │   ├── utils/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── db_helpers.py
│   │   │   │   ├── pagination.py
│   │   │   │   ├── sequencers.py
│   │   │   │   ├── updates.py
│   │   │   │   └── status.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── tenant.py
│   │   │   ├── usuario.py
│   │   │   ├── categoria.py
│   │   │   ├── produto.py
│   │   │   ├── fornecedor.py
│   │   │   ├── cotacao.py
│   │   │   └── pedido.py
│   │   ├── schemas/
│   │   │   ├── tenant.py
│   │   │   ├── usuario.py
│   │   │   ├── categoria.py
│   │   │   ├── produto.py
│   │   │   ├── fornecedor.py
│   │   │   ├── cotacao.py
│   │   │   └── pedido.py
│   │   └── main.py
│   ├── alembic/
│   │   └── versions/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── PageLayout.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useModal.ts
│   │   │   └── useCrudResource.ts
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Categorias.tsx
│   │   │   ├── Produtos.tsx
│   │   │   ├── Fornecedores.tsx
│   │   │   ├── Cotacoes.tsx
│   │   │   ├── Propostas.tsx
│   │   │   ├── MapaComparativo.tsx
│   │   │   ├── SugestaoIA.tsx
│   │   │   └── Pedidos.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── utils/
│   │   │   ├── formatters.ts
│   │   │   └── statusConfig.ts
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── PROGRESSO.md
```

---

## Como Executar

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

**URLs:**
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- Swagger Docs: http://localhost:8000/docs

---

## Proximos Passos Recomendados

1. **FASE 5 - Recebimento**: Completar o ciclo de compras
2. **FASE 6 - Relatorios**: Dashboard com metricas
3. **Testes**: Adicionar testes unitarios e de integracao
4. **Deploy**: Configurar Docker e CI/CD
