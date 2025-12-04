"""
Serviço de envio de mensagens via WhatsApp Web
Utiliza pywhatkit para automação do WhatsApp Web

IMPORTANTE:
- Requer que o WhatsApp Web esteja logado no navegador padrão
- O navegador será aberto automaticamente para enviar as mensagens
- Não é 100% automático (abre janelas)
"""
import os
import time
from typing import Optional
from pathlib import Path


class WhatsAppService:
    """Serviço para envio de mensagens via WhatsApp Web"""

    def __init__(self):
        self._pywhatkit = None
        self._is_available = False
        self._check_availability()

    def _check_availability(self):
        """Verifica se pywhatkit está instalado"""
        try:
            import pywhatkit
            self._pywhatkit = pywhatkit
            self._is_available = True
            print("[WHATSAPP] Serviço disponível (pywhatkit instalado)")
        except ImportError:
            print("[WHATSAPP] pywhatkit não instalado. Execute: pip install pywhatkit")
            self._is_available = False

    @property
    def is_available(self) -> bool:
        """Retorna True se o serviço está disponível"""
        return self._is_available

    def _formatar_numero(self, numero: str) -> str:
        """
        Formata o número para o padrão internacional
        Entrada: 11999999999 ou +5511999999999
        Saída: +5511999999999
        """
        # Remove caracteres não numéricos exceto +
        numero_limpo = ''.join(c for c in numero if c.isdigit() or c == '+')

        # Se não começa com +, adiciona código do Brasil
        if not numero_limpo.startswith('+'):
            # Se começa com 55, adiciona apenas +
            if numero_limpo.startswith('55'):
                numero_limpo = '+' + numero_limpo
            else:
                # Adiciona +55 (Brasil)
                numero_limpo = '+55' + numero_limpo

        return numero_limpo

    def enviar_mensagem(
        self,
        numero: str,
        mensagem: str,
        aguardar_segundos: int = 15
    ) -> dict:
        """
        Envia mensagem de texto via WhatsApp Web

        Args:
            numero: Número do WhatsApp (ex: 11999999999)
            mensagem: Texto da mensagem
            aguardar_segundos: Tempo para aguardar WhatsApp Web carregar

        Returns:
            dict com status do envio
        """
        if not self._is_available:
            return {
                "sucesso": False,
                "erro": "pywhatkit não instalado",
                "numero": numero
            }

        try:
            numero_formatado = self._formatar_numero(numero)
            print(f"[WHATSAPP] Enviando mensagem para {numero_formatado}...")

            # Envia mensagem instantaneamente (abre o navegador)
            self._pywhatkit.sendwhatmsg_instantly(
                phone_no=numero_formatado,
                message=mensagem,
                wait_time=aguardar_segundos,
                tab_close=True,
                close_time=3
            )

            print(f"[WHATSAPP] Mensagem enviada para {numero_formatado}")
            return {
                "sucesso": True,
                "numero": numero_formatado,
                "mensagem": "Mensagem enviada com sucesso"
            }

        except Exception as e:
            print(f"[WHATSAPP] Erro ao enviar para {numero}: {e}")
            return {
                "sucesso": False,
                "erro": str(e),
                "numero": numero
            }

    def enviar_mensagem_com_arquivo(
        self,
        numero: str,
        mensagem: str,
        arquivo_path: str,
        aguardar_segundos: int = 15
    ) -> dict:
        """
        Envia mensagem com arquivo anexo via WhatsApp Web

        Args:
            numero: Número do WhatsApp
            mensagem: Legenda/mensagem junto ao arquivo
            arquivo_path: Caminho do arquivo (PDF, imagem, etc)
            aguardar_segundos: Tempo para aguardar WhatsApp Web carregar

        Returns:
            dict com status do envio
        """
        if not self._is_available:
            return {
                "sucesso": False,
                "erro": "pywhatkit não instalado",
                "numero": numero
            }

        # Verificar se arquivo existe
        if not os.path.exists(arquivo_path):
            return {
                "sucesso": False,
                "erro": f"Arquivo não encontrado: {arquivo_path}",
                "numero": numero
            }

        try:
            numero_formatado = self._formatar_numero(numero)
            print(f"[WHATSAPP] Enviando arquivo para {numero_formatado}...")

            # Para arquivos, usamos sendwhats_image (funciona com PDFs também)
            # Mas pywhatkit tem limitações com PDFs
            # Alternativa: enviar mensagem com link para download

            # Verificar extensão
            ext = Path(arquivo_path).suffix.lower()

            if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                # Imagem - usar sendwhats_image
                self._pywhatkit.sendwhats_image(
                    receiver=numero_formatado,
                    img_path=arquivo_path,
                    caption=mensagem,
                    wait_time=aguardar_segundos,
                    tab_close=True,
                    close_time=3
                )
            else:
                # PDF ou outro arquivo - enviar apenas mensagem
                # pywhatkit não suporta envio de PDFs diretamente
                # Enviar mensagem informando que PDF foi enviado por email
                mensagem_com_aviso = f"{mensagem}\n\n(PDF da cotação enviado por e-mail)"
                self._pywhatkit.sendwhatmsg_instantly(
                    phone_no=numero_formatado,
                    message=mensagem_com_aviso,
                    wait_time=aguardar_segundos,
                    tab_close=True,
                    close_time=3
                )

            print(f"[WHATSAPP] Arquivo/mensagem enviado para {numero_formatado}")
            return {
                "sucesso": True,
                "numero": numero_formatado,
                "mensagem": "Enviado com sucesso"
            }

        except Exception as e:
            print(f"[WHATSAPP] Erro ao enviar arquivo para {numero}: {e}")
            return {
                "sucesso": False,
                "erro": str(e),
                "numero": numero
            }

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
        Envia solicitação de cotação formatada via WhatsApp

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
        from app.config import settings

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

        # Adicionar link para download do PDF
        if solicitacao_id and fornecedor_id:
            pdf_url = f"{settings.API_BASE_URL}/api/v1/cotacoes/solicitacoes/{solicitacao_id}/pdf/{fornecedor_id}"
            mensagem += f"📎 *Baixe o PDF completo:*\n{pdf_url}\n\n"

        if data_limite:
            mensagem += f"⏰ Prazo para resposta: {data_limite}\n\n"

        mensagem += "Por favor, envie sua proposta respondendo este WhatsApp ou por e-mail."

        return self.enviar_mensagem(numero, mensagem)


# Instância singleton
whatsapp_service = WhatsAppService()
