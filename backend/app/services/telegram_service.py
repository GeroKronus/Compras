"""
Serviço de Notificações via Telegram
Envia alertas quando propostas são recebidas por email
Configurações por tenant (multi-tenant)
"""
import requests
from datetime import datetime
from typing import Optional


class TelegramService:
    """
    Serviço para enviar notificações via Telegram Bot API
    Configurações são passadas por tenant (não usa variáveis globais)
    """

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None, enabled: bool = False):
        """
        Inicializa o serviço com configurações do tenant

        Args:
            token: Bot token do Telegram
            chat_id: ID do chat/grupo para enviar mensagens
            enabled: Se as notificações estão habilitadas
        """
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled

    @classmethod
    def from_tenant(cls, tenant) -> 'TelegramService':
        """
        Cria instância a partir de um objeto Tenant

        Args:
            tenant: Objeto Tenant do SQLAlchemy

        Returns:
            Instância configurada do TelegramService
        """
        return cls(
            token=tenant.telegram_bot_token,
            chat_id=tenant.telegram_chat_id,
            enabled=tenant.telegram_enabled or False
        )

    @property
    def is_configured(self) -> bool:
        """Verifica se o Telegram está configurado"""
        return bool(self.token and self.chat_id and self.enabled)

    def _send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envia mensagem via Telegram Bot API

        Args:
            message: Texto da mensagem (suporta HTML)
            parse_mode: Modo de parse (HTML ou Markdown)

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        if not self.is_configured:
            print("[TELEGRAM] Não configurado - pulando notificação")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }

        try:
            response = requests.post(url, data=payload, timeout=10)
            if response.ok:
                print(f"[TELEGRAM] Mensagem enviada com sucesso")
                return True
            else:
                print(f"[TELEGRAM] Erro HTTP {response.status_code}: {response.text}")
                return False
        except requests.exceptions.Timeout:
            print("[TELEGRAM] Timeout ao enviar mensagem (>10s)")
            return False
        except Exception as e:
            print(f"[TELEGRAM] Erro ao enviar: {e}")
            return False

    def notificar_proposta_recebida(
        self,
        numero_sc: str,
        fornecedor_nome: str,
        valor_total: Optional[float] = None,
        prazo_entrega: Optional[int] = None,
        total_propostas: int = 1,
        total_fornecedores: int = 1
    ) -> bool:
        """
        Notifica que uma proposta foi recebida

        Args:
            numero_sc: Número da solicitação de cotação (ex: SC-2025-00001)
            fornecedor_nome: Nome do fornecedor
            valor_total: Valor total da proposta (opcional)
            prazo_entrega: Prazo de entrega em dias (opcional)
            total_propostas: Quantas propostas já foram recebidas para esta SC
            total_fornecedores: Total de fornecedores que receberam a SC

        Returns:
            True se enviou com sucesso
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Monta a mensagem
        linhas = [
            "📬 <b>PROPOSTA RECEBIDA</b>",
            f"⏰ {timestamp}",
            "",
            f"📋 <b>Solicitação:</b> {numero_sc}",
            f"🏢 <b>Fornecedor:</b> {fornecedor_nome}",
        ]

        if valor_total is not None:
            linhas.append(f"💰 <b>Valor Total:</b> R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        if prazo_entrega is not None:
            linhas.append(f"📅 <b>Prazo:</b> {prazo_entrega} dias")

        linhas.append("")
        linhas.append(f"📊 <b>Status:</b> {total_propostas}/{total_fornecedores} propostas recebidas")

        if total_propostas >= total_fornecedores:
            linhas.append("")
            linhas.append("✅ <i>Todas as propostas foram recebidas!</i>")
            linhas.append("👉 Acesse o sistema para analisar e gerar a Ordem de Compra.")

        mensagem = "\n".join(linhas)
        return self._send_message(mensagem)

    def notificar_erro_processamento(
        self,
        numero_sc: str,
        erro: str
    ) -> bool:
        """
        Notifica que houve erro ao processar uma proposta

        Args:
            numero_sc: Número da SC
            erro: Descrição do erro

        Returns:
            True se enviou com sucesso
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        mensagem = "\n".join([
            "⚠️ <b>ERRO NO PROCESSAMENTO</b>",
            f"⏰ {timestamp}",
            "",
            f"📋 <b>Solicitação:</b> {numero_sc}",
            f"❌ <b>Erro:</b> {erro}",
            "",
            "👉 Verifique o email manualmente no sistema."
        ])

        return self._send_message(mensagem)

    def notificar_resumo_diario(
        self,
        total_scs_abertas: int,
        total_propostas_recebidas: int,
        scs_completas: list
    ) -> bool:
        """
        Envia resumo diário das cotações

        Args:
            total_scs_abertas: Quantas SCs estão abertas aguardando propostas
            total_propostas_recebidas: Total de propostas recebidas hoje
            scs_completas: Lista de SCs que estão com todas as propostas

        Returns:
            True se enviou com sucesso
        """
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

        linhas = [
            "📊 <b>RESUMO DE COTAÇÕES</b>",
            f"⏰ {timestamp}",
            "",
            f"📋 <b>SCs Abertas:</b> {total_scs_abertas}",
            f"📬 <b>Propostas Hoje:</b> {total_propostas_recebidas}",
        ]

        if scs_completas:
            linhas.append("")
            linhas.append("✅ <b>Prontas para análise:</b>")
            for sc in scs_completas[:5]:  # Máximo 5
                linhas.append(f"  • {sc}")
            if len(scs_completas) > 5:
                linhas.append(f"  <i>...e mais {len(scs_completas) - 5}</i>")

        mensagem = "\n".join(linhas)
        return self._send_message(mensagem)
