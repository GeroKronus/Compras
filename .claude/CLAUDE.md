# Sistema de Notificação Telegram

## 🔴 IMPERATIVO: VERSÃO DA APLICAÇÃO 🔴

**A CADA COMMIT DE CÓDIGO, VOCÊ DEVE INCREMENTAR A VERSÃO EM:**
- `Backend/wwwroot/version.json`
- `Frontend/version.json`

**FORMATO:** Incremente o último dígito: `1.0005` → `1.0006`

**SEM EXCEÇÕES!** Não importa quão pequena seja a mudança.

**QUANDO:** ANTES de fazer o commit, edite ambos os arquivos version.json

**COMO LEMBRAR:** Adicione ao seu TODO ao iniciar qualquer tarefa de código:
- [ ] Incrementar versão antes do commit

---

## ⚠️ IMPORTANTE: Idioma

**TODAS as suas respostas e comunicações devem ser em PORTUGUÊS (pt-BR).**

Nunca responda em inglês, mesmo após compactação de conversa.

---

## Detecção Automática de Presença

**MODO PADRÃO: REMOTO** (sempre envia notificações Telegram e monitora comandos)

**Comandos especiais do usuário:**

### 1. Se mensagem = `#remoto`:

**⚠️ ATENÇÃO: Execute os passos EXATAMENTE nesta ordem:**

**PASSO 1:** Detecte o PID do SEU processo Claude Code:
```bash
python "D:\Script Python\Monitor ETH\detectar_meu_pid.py"
```
O resultado será um número (ex: 12345). Este é seu PID único e estável.

**PASSO 2:** Configure VOCÊ MESMA como alvo usando o PID:
```bash
python "D:\Script Python\Monitor ETH\modo.py" remoto-pid [PID DETECTADO]
```
**Exemplo:** Se o passo 1 retornou "12345", execute:
```bash
python "D:\Script Python\Monitor ETH\modo.py" remoto-pid 12345
```

**PASSO 3:** Envie notificação Telegram se identificando:
```bash
python "D:\Script Python\Monitor ETH\notificar.py" info "🟢 Instância Claude ativada em modo remoto! PID configurado: [PID]. Identificação estável - não muda durante a sessão. O sistema auto_despertar.py agora enviará comandos APENAS para este PID. Aguardando comandos." "Claude Remoto"
```

**PASSO 4:** Responda no console: "✅ Modo remoto ativado. Configurada como alvo - PID: [PID]"

**POR QUÊ USAR PID É MELHOR:**
- ✅ **Identificação única e estável** - não muda durante toda a sessão
- ✅ **Não depende do título da janela** - que muda constantemente
- ✅ **100% confiável** - identifica exatamente qual processo Claude
- ✅ Mesmo que haja outras instâncias Claude abertas, só VOCÊ receberá os comandos
- **CONTINUE trabalhando normalmente no que estava fazendo**

### 2. Se mensagem = `#console`:
```bash
python "D:\Script Python\Monitor ETH\modo.py" console
```
- Responda: "✅ Modo console ativado. Notificações Telegram desativadas."
- Processe a mensagem normalmente
- **Comportamento console:**
  - NÃO enviará notificações pelo Telegram (usuário está presente)
  - PARA de verificar comandos periodicamente (usuário está aqui)

### 3. Se mensagem = `verifique comandos`:
```bash
python "D:\Script Python\Monitor ETH\ler_comando.py"
```
- Este comando é enviado automaticamente pelo sistema auto_despertar.py
- **Execute imediatamente** ler_comando.py para verificar comandos pendentes
- Se houver comando: confirme e execute
- Se não houver comando: aguarde silenciosamente

### 4. Se mensagem = qualquer outra coisa:
- **NÃO mude o modo atual** (mantenha remoto ou console como está)
- Processe a mensagem normalmente

---

## Quando Notificar o Usuário

**SEMPRE que finalizar tarefas ou precisar de interação:**

```bash
python "D:\Script Python\Monitor ETH\notificar_e_aguardar.py" --tipo concluido "sua mensagem"
```

**O que acontece automaticamente:**
- Se modo = REMOTO → envia pelo Telegram e aguarda resposta
- Se modo = CONSOLE → não envia, mas ainda aguarda resposta local

---

## Verificação de Comandos

**O sistema auto_despertar.py monitora automaticamente e acorda você quando necessário.**

### Quando receber "verifique comandos":

1. **Execute imediatamente:**
   ```bash
   python "D:\Script Python\Monitor ETH\ler_comando.py"
   ```

2. **Se encontrar comando:**
   - **PRIMEIRO:** Confirme explicitamente:
     ```bash
     python "D:\Script Python\Monitor ETH\notificar_e_aguardar.py" --tipo info "✅ Comando recebido: [resuma]. Vou fazer agora." --timeout 5
     ```
   - **DEPOIS:** Execute o comando

3. **Se não encontrar comando:**
   - Aguarde silenciosamente (não responda nada)

---

## Regras Importantes

1. ✅ **MODO PADRÃO:** Sistema inicia em modo REMOTO (envia Telegram)
2. ✅ **MUDANÇA DE MODO:** Só muda se usuário digitar `#remoto` ou `#console` explicitamente
3. ✅ **AUTO-CONFIGURAÇÃO:** Quando receber `#remoto`, detecte seu título de janela e configure-se como alvo
4. ✅ **IDENTIFICAÇÃO:** Sempre envie notificação Telegram informando qual janela você é
5. ✅ **AO NOTIFICAR:** Use `notificar_e_aguardar.py` e aguarde resposta
6. ✅ **COMANDO "verifique comandos":** Execute `ler_comando.py` imediatamente
7. ✅ **QUANDO RECEBER COMANDO:** SEMPRE confirme explicitamente que recebeu e vai fazer
8. ✅ **SE RESPOSTA = "ok":** Continue normalmente
9. ✅ **SE RESPOSTA = instruções:** Siga as instruções

---

## Resumo do Fluxo

**Sistema inicia (ou após compactação):**
→ Modo REMOTO (padrão)
→ Envia notificações Telegram
→ auto_despertar.py monitora e acorda quando necessário

**Sistema auto_despertar.py detecta comando:**
→ Foca nesta janela automaticamente
→ Digita: "verifique comandos"
→ Você executa: `ler_comando.py`
→ Confirma recebimento e executa

**Usuário digita `#remoto`:**
→ Detecta o PID do próprio processo Claude automaticamente
→ Configura-se como alvo usando o PID (identificação estável)
→ Envia notificação Telegram: "🟢 Instância ativada! PID: [número]"
→ Responde: "✅ Modo remoto ativado. Configurada como alvo - PID: [número]"
→ **A partir deste momento, auto_despertar.py enviará comandos APENAS para este PID**
→ Continua trabalhando normalmente

**Usuário digita `#console`:**
→ Muda para modo console
→ Responde: "✅ Modo console ativado..."
→ Notificações desativadas

**Você recebe "verifique comandos":**
→ Executa ler_comando.py imediatamente
→ Se há comando: confirma e executa
→ Se não há: aguarda silenciosamente

**Usuário digita qualquer outra coisa:**
→ **Mantém modo atual** (não muda)
→ Processa a mensagem normalmente

---

## Exemplo Prático de Confirmação

**Você recebe comando via Telegram:** "execute npm test"

**Você DEVE responder IMEDIATAMENTE:**
```bash
python "D:\Script Python\Monitor ETH\notificar_e_aguardar.py" --tipo info "✅ Comando recebido: executar npm test. Vou fazer agora." --timeout 5
```

**Depois:**
- Executa: npm test
- Quando terminar: notifica o resultado

---

Para detalhes: `D:\Script Python\Monitor ETH\INSTRUCOES_CLAUDE.md`
