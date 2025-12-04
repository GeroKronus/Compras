"""
Serviço de envio de mensagens via WhatsApp usando Twilio API (Multi-Tenant)

Cada tenant configura suas próprias credenciais Twilio.
"""
from typing import Optional
from app.config import settings


class TwilioWhatsAppService:
    """Serviço para envio de mensagens via WhatsApp usando Twilio (Multi-Tenant)"""

    def __init__(self):
        self._twilio_available = False
        self._check_twilio_installed()

    def _check_twilio_installed(self):
        """Verifica se a biblioteca Twilio está instalada"""
        try:
            from twilio.rest import Client
            self._twilio_available = True
            print("[TWILIO] Biblioteca disponível")
        except ImportError:
            print("[TWILIO] Biblioteca twilio não instalada. Execute: pip install twilio")
            self._twilio_available = False

    def _get_client(self, account_sid: str, auth_token: str):
        """Cria um cliente Twilio com as credenciais fornecidas"""
        if not self._twilio_available:
            return None
        from twilio.rest import Client
        return Client(account_sid, auth_token)

    def _formatar_numero(self, numero: str) -> str:
        """
        Formata o número para o padrão Twilio WhatsApp
        Entrada: 11999999999 ou +5511999999999
        Saída: whatsapp:+5511999999999
        """
        # Remove caracteres não numéricos exceto +
        numero_limpo = ''.join(c for c in numero if c.isdigit() or c == '+')

        # Se não começa com +, adiciona código do Brasil
        if not numero_limpo.startswith('+'):
            if numero_limpo.startswith('55'):
                numero_limpo = '+' + numero_limpo
            else:
                numero_limpo = '+55' + numero_limpo

        return f"whatsapp:{numero_limpo}"

    def is_configured(self, tenant) -> bool:
        """Verifica se o tenant tem WhatsApp configurado"""
        if not self._twilio_available:
            return False
        if not tenant:
            return False
        return (
            tenant.whatsapp_enabled and
            tenant.twilio_account_sid and
            tenant.twilio_auth_token and
            tenant.twilio_whatsapp_from
        )

    def enviar_mensagem(
        self,
        tenant,
        numero: str,
        mensagem: str,
        media_url: Optional[str] = None
    ) -> dict:
        """
        Envia mensagem de texto via WhatsApp

        Args:
            tenant: Objeto Tenant com credenciais Twilio
            numero: Número do WhatsApp (ex: 11999999999)
            mensagem: Texto da mensagem
            media_url: URL pública do arquivo para anexar (opcional)

        Returns:
            dict com status do envio
        """
        if not self._twilio_available:
            return {
                "sucesso": False,
                "erro": "Biblioteca Twilio não instalada",
                "numero": numero
            }

        if not self.is_configured(tenant):
            return {
                "sucesso": False,
                "erro": "WhatsApp não configurado para esta empresa. Configure nas configurações do tenant.",
                "numero": numero
            }

        try:
            client = self._get_client(tenant.twilio_account_sid, tenant.twilio_auth_token)
            numero_formatado = self._formatar_numero(numero)

            print(f"[TWILIO] Enviando mensagem para {numero_formatado} (Tenant: {tenant.nome_empresa})...")

            # Parâmetros da mensagem
            message_params = {
                "from_": tenant.twilio_whatsapp_from,
                "to": numero_formatado,
                "body": mensagem
            }

            # Adicionar mídia se fornecida
            if media_url:
                message_params["media_url"] = [media_url]
                print(f"[TWILIO] Anexando mídia: {media_url}")

            # Enviar mensagem
            message = client.messages.create(**message_params)

            print(f"[TWILIO] Mensagem enviada! SID: {message.sid}")
            return {
                "sucesso": True,
                "numero": numero_formatado,
                "message_sid": message.sid,
                "mensagem": "Mensagem enviada com sucesso"
            }

        except Exception as e:
            print(f"[TWILIO] Erro ao enviar para {numero}: {e}")
            return {
                "sucesso": False,
                "erro": str(e),
                "numero": numero
            }

    def enviar_mensagem_com_pdf(
        self,
        tenant,
        numero: str,
        mensagem: str,
        pdf_url: str
    ) -> dict:
        """
        Envia mensagem com PDF anexo via WhatsApp

        Args:
            tenant: Objeto Tenant com credenciais Twilio
            numero: Número do WhatsApp
            mensagem: Texto da mensagem
            pdf_url: URL pública do PDF

        Returns:
            dict com status do envio
        """
        return self.enviar_mensagem(tenant, numero, mensagem, media_url=pdf_url)

    def enviar_solicitacao_cotacao(
        self,
        tenant,
        numero: str,
        fornecedor_nome: str,
        solicitacao_numero: str,
        itens: list,
        data_limite: Optional[str] = None,
        solicitacao_id: Optional[int] = None,
        fornecedor_id: Optional[int] = None
    ) -> dict:
        """
        Envia solicitação de cotação formatada via WhatsApp com PDF anexo

        Args:
            tenant: Objeto Tenant com credenciais Twilio
            numero: WhatsApp do fornecedor
            fornecedor_nome: Nome do fornecedor
            solicitacao_numero: Número da SC (ex: SC-2025-00007)
            itens: Lista de itens [{produto_nome, quantidade, unidade_medida}]
            data_limite: Data limite para resposta (opcional)
            solicitacao_id: ID da solicitação (para gerar link do PDF)
            fornecedor_id: ID do fornecedor (para gerar link do PDF)

        Returns:
            dict com status do envio
        """
        # Montar mensagem formatada
        mensagem = f"*Solicitação de Cotação {solicitacao_numero}*\n\n"
        mensagem += f"Prezado(a) {fornecedor_nome},\n\n"
        mensagem += "Solicitamos cotação para os seguintes itens:\n\n"

        for item in itens:
            nome = item.get('produto_nome', 'Produto')
            qtd = item.get('quantidade', 1)
            unidade = item.get('unidade_medida', 'UN')
            mensagem += f"• {nome} - {qtd} {unidade}\n"

        mensagem += "\n"

        if data_limite:
            mensagem += f"⏰ Prazo para resposta: {data_limite}\n\n"

        mensagem += "Por favor, envie sua proposta respondendo este WhatsApp ou por e-mail."

        # Gerar URL do PDF se tivermos os IDs
        pdf_url = None
        if solicitacao_id and fornecedor_id:
            pdf_url = f"{settings.API_BASE_URL}/api/v1/cotacoes/solicitacoes/{solicitacao_id}/pdf/{fornecedor_id}"
            mensagem += f"\n\n📎 PDF da cotação anexado."

        return self.enviar_mensagem(tenant, numero, mensagem, media_url=pdf_url)


# Instância singleton
twilio_whatsapp_service = TwilioWhatsAppService()
