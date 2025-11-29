# Constantes e Padrões do Sistema de Compras

**ESTE ARQUIVO DEVE SER CONSULTADO ANTES DE QUALQUER ALTERAÇÃO NO CÓDIGO**

## 1. Modelo Claude (Anthropic API)

```
MODEL = "claude-sonnet-4-20250514"
```

**NUNCA USE:**
- `claude-3-5-sonnet-20241022` (descontinuado, retorna 404)
- Qualquer modelo sem verificar a documentação atual da Anthropic

**REGRA:** Antes de qualquer alteração em `ai_service.py`, verificar se o modelo ainda existe.

---

## 2. Formato de Números de Solicitação

O sistema usa o formato **SC-YYYY-NNNNN**:
- SC = Solicitação de Cotação
- YYYY = Ano (4 dígitos)
- NNNNN = Número sequencial (5 dígitos)

**Exemplo:** `SC-2025-00001`

**PADRÕES REGEX para classificação de emails:**
```python
# Padrão principal - SEMPRE incluir ambos formatos
r'SC-\d{4}-(\d+)'   # SC-2025-00001
r'SOL-\d{4}-(\d+)'  # SOL-2024-0001 (formato legado, manter compatibilidade)
```

**NUNCA:**
- Assumir apenas um formato (SC ou SOL)
- Esquecer de buscar pelo número formatado completo além do ID numérico

---

## 3. Fornecedores Cadastrados (Tenant 3 - Produção)

| ID | Nome | Email Principal |
|----|------|-----------------|
| 1 | Kronus | rogerio@isidorio.com.br |
| 2 | Picstone | rogerio@picstone.com.br |

**ATENÇÃO:** `patricia@kronus.com.br` NÃO está cadastrado no sistema.

---

## 4. URLs do Sistema

| Ambiente | URL |
|----------|-----|
| Produção Railway | https://compras-production-2ccb.up.railway.app |
| Banco PostgreSQL | shinkansen.proxy.rlwy.net:49885/railway |

**NUNCA:** Usar URLs antigas ou inventadas (ex: `b28a` não existe).

---

## 5. Credenciais de Email (IMAP/SMTP)

```
Host: imappro.zoho.com (IMAP), smtp.zoho.com (SMTP)
Porta: 993 (IMAP), 465 (SMTP)
Usuário: contato@picstone.com.br
```

---

## 6. Arquivos de Versão

Incrementar versão em TODOS os arquivos a cada commit:
- `backend/app/main.py` (linha com `return {"version":`)
- `backend/app/api/routes/setup.py` (endpoint `/version`)
- `backend/wwwroot/version.json`
- `frontend/version.json`

**Formato:** `1.XXXX` (ex: 1.0046, 1.0047)

---

## 7. Erros Comuns a Evitar

### 7.1 Modelo Claude não encontrado (404)
**Causa:** Nome do modelo desatualizado
**Solução:** Verificar modelo atual em ai_service.py

### 7.2 Emails não classificados
**Causa:** Padrão regex não reconhece formato do número
**Solução:** Verificar se padrões SC e SOL estão ambos incluídos

### 7.3 Propostas não criadas
**Causa:** Código só busca propostas existentes, não cria novas
**Solução:** Função `_marcar_proposta_recebida` deve CRIAR se não existir

### 7.4 Fornecedor não encontrado
**Causa:** Email do remetente não está cadastrado no sistema
**Solução:** Verificar tabela `fornecedores` antes de assumir erro no código

---

## 8. Checklist Antes de Deploy

- [ ] Versão incrementada em TODOS os arquivos
- [ ] Modelo Claude é `claude-sonnet-4-20250514`
- [ ] Padrões SC e SOL estão ambos cobertos
- [ ] Funções criam registros quando necessário (não apenas buscam)
- [ ] Endpoints de debug estão no middleware PUBLIC_PREFIXES

---

**Última atualização:** 2025-11-29 - Versão 1.0046
