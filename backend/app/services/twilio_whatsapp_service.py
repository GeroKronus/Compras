"""
Serviço de envio de mensagens via WhatsApp usando Twilio API

Vantagens sobre pywhatkit:
- Funciona em servidor (nuvem)
- Não precisa de navegador
- Suporta envio de PDFs
- Profissional e confiável
"""
from typing import Optional, List
from app.config import settings


class TwilioWhatsAppService:
    """Serviço para envio de mensagens via WhatsApp usando Twilio"""

    def __init__(self):
        self._client = None
        self._is_available = False
        self._check_availability()

    def _check_availability(self):
        """Verifica se Twilio está configurado"""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            print("[TWILIO] Credenciais não configuradas. Configure TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN no .env")
            self._is_available = False
            return

        try:
            from twilio.rest import Client
            self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self._is_available = True
            print("[TWILIO] Serviço WhatsApp disponível")
        except ImportError:
            print("[TWILIO] Biblioteca twilio não instalada. Execute: pip install twilio")
            self._is_available = False
        except Exception as e:
            print(f"[TWILIO] Erro ao inicializar: {e}")
            self._is_available = False

    @property
    def is_available(self) -> bool:
        """Retorna True se o serviço está disponível"""
        return self._is_available

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

    def enviar_mensagem(
        self,
        numero: str,
        mensagem: str,
        media_url: Optional[str] = None
    ) -> dict:
        """
        Envia mensagem de texto via WhatsApp

        Args:
            numero: Número do WhatsApp (ex: 11999999999)
            mensagem: Texto da mensagem
            media_url: URL pública do arquivo para anexar (opcional)

        Returns:
            dict com status do envio
        """
        if not self._is_available:
            return {
                "sucesso": False,
                "erro": "Twilio não configurado. Verifique as credenciais no .env",
                "numero": numero
            }

        if not settings.TWILIO_WHATSAPP_FROM:
            return {
                "sucesso": False,
                "erro": "TWILIO_WHATSAPP_FROM não configurado no .env",
                "numero": numero
            }

        try:
            numero_formatado = self._formatar_numero(numero)
            print(f"[TWILIO] Enviando mensagem para {numero_formatado}...")

            # Parâmetros da mensagem
            message_params = {
                "from_": settings.TWILIO_WHATSAPP_FROM,
                "to": numero_formatado,
                "body": mensagem
            }

            # Adicionar mídia se fornecida
            if media_url:
                message_params["media_url"] = [media_url]
                print(f"[TWILIO] Anexando mídia: {media_url}")

            # Enviar mensagem
            message = self._client.messages.create(**message_params)

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
        numero: str,
        mensagem: str,
        pdf_url: str
    ) -> dict:
        """
        Envia mensagem com PDF anexo via WhatsApp

        Args:
            numero: Número do WhatsApp
            mensagem: Texto da mensagem
            pdf_url: URL pública do PDF

        Returns:
            dict com status do envio
        """
        return self.enviar_mensagem(numero, mensagem, media_url=pdf_url)

    def enviar_solicitacao_cotacao(
        self,
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

        return self.enviar_mensagem(numero, mensagem, media_url=pdf_url)


# Instância singleton
twilio_whatsapp_service = TwilioWhatsAppService()
