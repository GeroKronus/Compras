"""
Serviço de Email para Sistema de Compras
Envio via SMTP e Leitura via IMAP
Baseado no sistema PicStone WEB (Zoho Mail)
"""
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.header import decode_header
from email import encoders
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import re
from app.config import settings


class EmailService:
    """Serviço para envio e leitura de emails"""

    def __init__(self):
        self.smtp_host = getattr(settings, 'SMTP_HOST', 'smtppro.zoho.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 465)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.email_from = getattr(settings, 'EMAIL_FROM', self.smtp_user)

        # IMAP para leitura
        self.imap_host = getattr(settings, 'IMAP_HOST', 'imappro.zoho.com')
        self.imap_port = getattr(settings, 'IMAP_PORT', 993)

    @property
    def is_configured(self) -> bool:
        """Verifica se o serviço de email está configurado (verifica dinamicamente)"""
        smtp_user = getattr(settings, 'SMTP_USER', '')
        smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        return bool(smtp_user and smtp_password)

    def enviar_email(
        self,
        destinatario: str,
        assunto: str,
        corpo_html: str,
        corpo_texto: Optional[str] = None,
        anexos: Optional[List[Tuple[str, bytes]]] = None
    ) -> bool:
        """
        Envia email via SMTP

        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            corpo_html: Corpo do email em HTML
            corpo_texto: Corpo em texto puro (opcional)
            anexos: Lista de tuplas (nome_arquivo, bytes_conteudo)

        Returns:
            True se enviado com sucesso
        """
        # Recarregar configurações do settings (importante para Railway)
        smtp_host = getattr(settings, 'SMTP_HOST', 'smtppro.zoho.com')
        smtp_port = getattr(settings, 'SMTP_PORT', 465)
        smtp_user = getattr(settings, 'SMTP_USER', '')
        smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        email_from = getattr(settings, 'EMAIL_FROM', '') or smtp_user

        if not smtp_user or not smtp_password:
            print(f"[EMAIL] Serviço não configurado. SMTP_USER={bool(smtp_user)}, SMTP_PASSWORD={bool(smtp_password)}")
            return False

        try:
            # Criar mensagem mista (para suportar anexos)
            msg = MIMEMultipart('mixed')
            msg['From'] = email_from
            msg['To'] = destinatario
            msg['Subject'] = assunto

            # Parte do corpo (alternativa: texto/html)
            corpo_part = MIMEMultipart('alternative')
            if corpo_texto:
                corpo_part.attach(MIMEText(corpo_texto, 'plain', 'utf-8'))
            corpo_part.attach(MIMEText(corpo_html, 'html', 'utf-8'))
            msg.attach(corpo_part)

            # Adicionar anexos
            if anexos:
                for nome_arquivo, conteudo in anexos:
                    if nome_arquivo.lower().endswith('.pdf'):
                        anexo = MIMEApplication(conteudo, _subtype='pdf')
                    else:
                        anexo = MIMEBase('application', 'octet-stream')
                        anexo.set_payload(conteudo)
                        encoders.encode_base64(anexo)

                    anexo.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=nome_arquivo
                    )
                    msg.attach(anexo)
                    print(f"[EMAIL] Anexo adicionado: {nome_arquivo}")

            # Conectar e enviar via SSL (porta 465)
            print(f"[EMAIL] Conectando a {smtp_host}:{smtp_port}...")
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)

            print(f"[EMAIL] Fazendo login como {smtp_user}...")
            server.login(smtp_user, smtp_password)

            print(f"[EMAIL] Enviando de {email_from} para {destinatario}...")
            result = server.sendmail(email_from, destinatario, msg.as_string())

            server.quit()

            if result:
                print(f"[EMAIL] Alguns destinatários falharam: {result}")
            else:
                print(f"[EMAIL] Enviado com sucesso para: {destinatario}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"[EMAIL] ERRO de autenticação: {e.smtp_code} - {e.smtp_error}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            print(f"[EMAIL] Destinatário recusado: {e.recipients}")
            return False
        except smtplib.SMTPException as e:
            print(f"[EMAIL] ERRO SMTP ({type(e).__name__}): {e}")
            return False
        except Exception as e:
            print(f"[EMAIL] ERRO ao enviar para {destinatario}: {type(e).__name__} - {e}")
            return False

    def enviar_solicitacao_cotacao(
        self,
        fornecedor_email: str,
        fornecedor_nome: str,
        produto_nome: str,
        quantidade: int,
        unidade: str,
        observacoes: Optional[str] = None,
        solicitacao_id: int = 0,
        prazo_resposta_dias: int = 3
    ) -> bool:
        """
        Envia email de solicitação de cotação para fornecedor

        Args:
            fornecedor_email: Email do fornecedor
            fornecedor_nome: Nome do fornecedor
            produto_nome: Nome do produto
            quantidade: Quantidade desejada
            unidade: Unidade de medida
            observacoes: Observações adicionais
            solicitacao_id: ID da solicitação (para rastreamento)
            prazo_resposta_dias: Prazo para resposta

        Returns:
            True se enviado com sucesso
        """
        prazo = (datetime.now() + timedelta(days=prazo_resposta_dias)).strftime('%d/%m/%Y')

        assunto = f"[COTAÇÃO #{solicitacao_id}] Solicitação de Preço - {produto_nome}"

        obs_html = f"<p><strong>Observações:</strong> {observacoes}</p>" if observacoes else ""

        corpo_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .produto-box {{ background: white; border: 2px solid #3b82f6; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .importante {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
        th {{ background: #4caf50; color: white; padding: 10px; text-align: left; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Solicitação de Cotação</h1>
            <p style="margin: 10px 0 0 0;">Referência: #{solicitacao_id}</p>
        </div>
        <div class="content">
            <p>Prezado(a) <strong>{fornecedor_nome}</strong>,</p>

            <p>Gostaríamos de solicitar cotação para o seguinte item:</p>

            <div class="produto-box">
                <h3 style="margin-top: 0; color: #3b82f6;">{produto_nome}</h3>
                <p><strong>Quantidade:</strong> {quantidade} {unidade}</p>
                {obs_html}
            </div>

            <div style="background: #e8f5e9; border: 2px solid #4caf50; border-radius: 8px; padding: 20px; margin: 25px 0;">
                <h3 style="color: #2e7d32; margin-top: 0;">📝 PREENCHA SUA PROPOSTA ABAIXO</h3>
                <p style="color: #555; margin-bottom: 15px;">Ao responder, preencha os campos em amarelo com seus valores:</p>

                <table style="width: 100%; border-collapse: collapse; background: white;">
                    <thead>
                        <tr style="background: #4caf50; color: white;">
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Produto</th>
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center; width: 60px;">Qtd</th>
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center; width: 100px;">Preco Unit.</th>
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center; width: 100px;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd;">{produto_nome}</td>
                            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{quantidade}</td>
                            <td style="padding: 10px; border: 1px solid #ddd; text-align: center; background: #fffef0;">R$ _______</td>
                            <td style="padding: 10px; border: 1px solid #ddd; text-align: center; background: #fffef0;">R$ _______</td>
                        </tr>
                    </tbody>
                </table>

                <div style="margin-top: 15px; padding: 15px; background: #fffef0; border-radius: 5px;">
                    <p style="margin: 5px 0;"><strong>Prazo de Entrega:</strong> _______ dias</p>
                    <p style="margin: 5px 0;"><strong>Condicoes de Pagamento:</strong> _______________________</p>
                    <p style="margin: 5px 0;"><strong>Frete:</strong> ( ) Incluso ( ) Por conta do comprador - Valor: R$ _______</p>
                    <p style="margin: 5px 0;"><strong>Validade da Proposta:</strong> _______ dias</p>
                    <p style="margin: 5px 0;"><strong>Observacoes:</strong> _______________________</p>
                </div>
            </div>

            <div class="importante">
                <strong>⚠️ IMPORTANTE:</strong>
                <ul style="margin: 10px 0 0 0;">
                    <li>Preencha a tabela acima ao responder este email</li>
                    <li>Voce tambem pode anexar um PDF ou responder em formato livre</li>
                    <li>Prazo para resposta: <strong>{prazo}</strong></li>
                    <li>Mantenha o assunto do email para rastreamento</li>
                </ul>
            </div>

            <p>Aguardamos seu retorno.</p>

            <p>Atenciosamente,<br>
            <strong>Departamento de Compras</strong></p>
        </div>
        <div class="footer">
            <p>Este é um email automático do Sistema de Gestão de Compras</p>
            <p>Referência: COTACAO-{solicitacao_id}</p>
        </div>
    </div>
</body>
</html>
"""

        corpo_texto = f"""
Prezado(a) {fornecedor_nome},

Gostaríamos de solicitar cotação para o seguinte item:

PRODUTO: {produto_nome}
QUANTIDADE: {quantidade} {unidade}
{f'OBSERVAÇÕES: {observacoes}' if observacoes else ''}

============================================
   PREENCHA SUA PROPOSTA ABAIXO
============================================

{produto_nome} | Qtd: {quantidade} | Preco Unit: R$ _____ | Total: R$ _____

Prazo de Entrega: _______ dias
Condicoes de Pagamento: _______________________
Frete: ( ) Incluso ( ) Por conta do comprador - Valor: R$ _______
Validade da Proposta: _______ dias
Observacoes: _______________________

============================================

IMPORTANTE:
- Preencha os campos acima ao responder este email
- Voce tambem pode anexar um PDF ou responder em formato livre
- Prazo para resposta: {prazo}
- Mantenha o assunto do email para rastreamento

Atenciosamente,
Departamento de Compras

Referência: COTACAO-{solicitacao_id}
"""

        return self.enviar_email(
            destinatario=fornecedor_email,
            assunto=assunto,
            corpo_html=corpo_html,
            corpo_texto=corpo_texto
        )

    def enviar_solicitacao_cotacao_multiplos_itens(
        self,
        fornecedor_email: str,
        fornecedor_nome: str,
        solicitacao_numero: str,
        solicitacao_titulo: str,
        itens: List[dict],
        observacoes: Optional[str] = None,
        solicitacao_id: int = 0,
        data_limite: Optional[str] = None,
        prazo_resposta_dias: int = 5,
        fornecedor_cnpj: Optional[str] = None
    ) -> bool:
        """
        Envia email de solicitação de cotação com múltiplos itens para fornecedor
        Inclui PDF preenchível em anexo

        Args:
            fornecedor_email: Email do fornecedor
            fornecedor_nome: Nome do fornecedor
            solicitacao_numero: Número da solicitação (ex: SOL-2024-0001)
            solicitacao_titulo: Título da solicitação
            itens: Lista de itens com produto_nome, quantidade, unidade_medida, especificacoes
            observacoes: Observações adicionais
            solicitacao_id: ID da solicitação (para rastreamento)
            data_limite: Data limite para resposta
            prazo_resposta_dias: Prazo para resposta em dias (usado se data_limite não informada)
            fornecedor_cnpj: CNPJ do fornecedor

        Returns:
            True se enviado com sucesso
        """
        if data_limite:
            prazo = data_limite
        else:
            prazo = (datetime.now() + timedelta(days=prazo_resposta_dias)).strftime('%d/%m/%Y')

        assunto = f"[COTAÇÃO {solicitacao_numero}] {solicitacao_titulo}"

        # Criar HTML dos itens (tabela de visualização apenas)
        itens_html = ""
        itens_texto = ""

        for i, item in enumerate(itens, 1):
            especificacoes_html = f"<br><small style='color: #666;'>Obs: {item.get('especificacoes', '')}</small>" if item.get('especificacoes') else ""
            itens_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{i}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;"><strong>{item.get('produto_nome', 'N/A')}</strong>{especificacoes_html}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{item.get('quantidade', 0)}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{item.get('unidade_medida', 'UN')}</td>
            </tr>
            """
            especificacoes_texto = f" ({item.get('especificacoes', '')})" if item.get('especificacoes') else ""
            itens_texto += f"  {i}. {item.get('produto_nome', 'N/A')} - {item.get('quantidade', 0)} {item.get('unidade_medida', 'UN')}{especificacoes_texto}\n"

        obs_html = f"<p><strong>Observações:</strong> {observacoes}</p>" if observacoes else ""

        # Email simplificado - formulário está no PDF
        corpo_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .destaque {{ background: #e8f5e9; border: 2px solid #10b981; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
        .importante {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
        th {{ background: #3b82f6; color: white; padding: 12px; text-align: left; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Solicitação de Cotação</h1>
            <p style="margin: 10px 0 0 0;">{solicitacao_numero}</p>
        </div>
        <div class="content">
            <p>Prezado(a) <strong>{fornecedor_nome}</strong>,</p>

            <p>Gostaríamos de solicitar cotação para os seguintes itens:</p>

            <h3 style="color: #3b82f6; margin-top: 25px;">{solicitacao_titulo}</h3>

            <table>
                <thead>
                    <tr>
                        <th style="width: 50px;">#</th>
                        <th>Produto</th>
                        <th style="width: 80px; text-align: center;">Qtd</th>
                        <th style="width: 80px; text-align: center;">Unid</th>
                    </tr>
                </thead>
                <tbody>
                    {itens_html}
                </tbody>
            </table>

            {obs_html}

            <div class="destaque">
                <h3 style="color: #059669; margin: 0 0 10px 0;">📎 PDF EM ANEXO</h3>
                <p style="margin: 0;">Abra o <strong>PDF anexo</strong>, preencha os campos e responda este email com o arquivo preenchido.</p>
            </div>

            <div class="importante">
                <strong>⚠️ COMO RESPONDER:</strong>
                <ul style="margin: 10px 0 0 0;">
                    <li>Abra o PDF anexo no seu computador</li>
                    <li>Preencha os campos de preço, prazo e condições</li>
                    <li>Salve o PDF e anexe na resposta deste email</li>
                    <li>Prazo para resposta: <strong>{prazo}</strong></li>
                </ul>
            </div>

            <p>Aguardamos seu retorno.</p>

            <p>Atenciosamente,<br>
            <strong>Departamento de Compras</strong></p>
        </div>
        <div class="footer">
            <p>Este é um email automático do Sistema de Gestão de Compras</p>
            <p>Referência: {solicitacao_numero} | ID: {solicitacao_id}</p>
        </div>
    </div>
</body>
</html>
"""

        corpo_texto = f"""
Prezado(a) {fornecedor_nome},

Gostaríamos de solicitar cotação para os seguintes itens:

{solicitacao_titulo}
-------------------------------------------
{itens_texto}
{f'OBSERVAÇÕES: {observacoes}' if observacoes else ''}

============================================
   PDF EM ANEXO
============================================

Abra o PDF anexo, preencha os campos de preço, prazo e condições,
salve e responda este email com o arquivo preenchido.

Prazo para resposta: {prazo}

Atenciosamente,
Departamento de Compras

Referência: {solicitacao_numero} | ID: {solicitacao_id}
"""

        # Gerar PDF com formulário preenchível
        anexos = []
        try:
            from app.services.pdf_service import pdf_service

            pdf_bytes = pdf_service.gerar_pdf_cotacao(
                fornecedor_nome=fornecedor_nome,
                fornecedor_cnpj=fornecedor_cnpj,
                solicitacao_numero=solicitacao_numero,
                solicitacao_titulo=solicitacao_titulo,
                itens=itens,
                observacoes=observacoes,
                data_limite=prazo,
                solicitacao_id=solicitacao_id
            )

            nome_pdf = f"Cotacao_{solicitacao_numero.replace(' ', '_').replace('/', '-')}.pdf"
            anexos.append((nome_pdf, pdf_bytes))
            print(f"[EMAIL] PDF gerado: {nome_pdf} ({len(pdf_bytes)} bytes)")

        except Exception as e:
            print(f"[EMAIL] ERRO ao gerar PDF: {e}")
            # Continua sem o PDF

        return self.enviar_email(
            destinatario=fornecedor_email,
            assunto=assunto,
            corpo_html=corpo_html,
            corpo_texto=corpo_texto,
            anexos=anexos if anexos else None
        )

    def ler_emails_cotacao(
        self,
        solicitacao_id: int,
        dias_atras: int = 7
    ) -> List[dict]:
        """
        Lê emails de resposta relacionados a uma solicitação de cotação

        Args:
            solicitacao_id: ID da solicitação para filtrar
            dias_atras: Quantos dias para trás buscar

        Returns:
            Lista de emails encontrados com seus dados
        """
        if not self.is_configured:
            print("[EMAIL] Serviço não configurado. Pulando leitura.")
            return []

        emails_encontrados = []

        try:
            # Conectar via IMAP
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.smtp_user, self.smtp_password)
            mail.select('INBOX')

            # Buscar emails dos últimos N dias
            data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%d-%b-%Y')

            # Buscar emails com o ID da solicitação no assunto
            search_criteria = f'(SINCE "{data_inicio}" SUBJECT "COTAÇÃO #{solicitacao_id}")'

            status, messages = mail.search(None, search_criteria)

            if status != 'OK':
                print(f"[EMAIL] Nenhum email encontrado para solicitação #{solicitacao_id}")
                return []

            email_ids = messages[0].split()

            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extrair dados do email
                remetente = self._decode_header(msg['From'])
                assunto = self._decode_header(msg['Subject'])
                data = msg['Date']

                # Extrair corpo do email
                corpo = self._extrair_corpo(msg)

                # Extrair email do remetente
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', remetente)
                email_remetente = email_match.group(0) if email_match else remetente

                emails_encontrados.append({
                    'id': email_id.decode(),
                    'remetente': remetente,
                    'email_remetente': email_remetente,
                    'assunto': assunto,
                    'data': data,
                    'corpo': corpo
                })

            mail.logout()

            print(f"[EMAIL] Encontrados {len(emails_encontrados)} emails para solicitação #{solicitacao_id}")
            return emails_encontrados

        except Exception as e:
            print(f"[EMAIL] ERRO ao ler emails: {e}")
            return []

    def _decode_header(self, header: str) -> str:
        """Decodifica header de email"""
        if not header:
            return ""

        decoded_parts = decode_header(header)
        result = []

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                result.append(part)

        return ' '.join(result)

    def _extrair_corpo(self, msg) -> str:
        """Extrai corpo do email (prefere texto puro)"""
        corpo = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()

                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        corpo = payload.decode(charset, errors='ignore')
                        break
                elif content_type == 'text/html' and not corpo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        # Remove tags HTML básicas
                        html_content = payload.decode(charset, errors='ignore')
                        corpo = re.sub(r'<[^>]+>', ' ', html_content)
                        corpo = re.sub(r'\s+', ' ', corpo).strip()
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                corpo = payload.decode(charset, errors='ignore')

        return corpo


    def enviar_notificacao_vencedor(
        self,
        fornecedor_email: str,
        fornecedor_nome: str,
        solicitacao_numero: str,
        solicitacao_titulo: str,
        itens: List[dict],
        valor_total: float,
        prazo_entrega: Optional[int] = None,
        condicao_pagamento: Optional[str] = None
    ) -> bool:
        """
        Envia email de notificação ao fornecedor vencedor da cotação

        Args:
            fornecedor_email: Email do fornecedor
            fornecedor_nome: Nome do fornecedor
            solicitacao_numero: Número da solicitação (ex: SC-2024-0001)
            solicitacao_titulo: Título da solicitação
            itens: Lista de itens com produto_nome, quantidade, preco_unitario, preco_total
            valor_total: Valor total da proposta vencedora
            prazo_entrega: Prazo de entrega em dias
            condicao_pagamento: Condição de pagamento

        Returns:
            True se enviado com sucesso
        """
        assunto = f"[VENCEDOR] {solicitacao_numero} - Sua proposta foi aceita!"

        # Criar HTML dos itens
        itens_html = ""
        for i, item in enumerate(itens, 1):
            itens_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{i}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;"><strong>{item.get('produto_nome', 'N/A')}</strong></td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{item.get('quantidade', 0)}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">R$ {item.get('preco_unitario', 0):,.2f}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">R$ {item.get('preco_total', 0):,.2f}</td>
            </tr>
            """

        prazo_html = f"<p><strong>Prazo de Entrega:</strong> {prazo_entrega} dias</p>" if prazo_entrega else ""
        condicao_html = f"<p><strong>Condição de Pagamento:</strong> {condicao_pagamento}</p>" if condicao_pagamento else ""

        corpo_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .destaque {{ background: #ecfdf5; border: 2px solid #10b981; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
        th {{ background: #10b981; color: white; padding: 12px; text-align: left; }}
        .total {{ background: #f0fdf4; font-weight: bold; }}
        .proximos-passos {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">🎉 Parabéns!</h1>
            <p style="margin: 10px 0 0 0; font-size: 18px;">Sua proposta foi aceita!</p>
        </div>
        <div class="content">
            <p>Prezado(a) <strong>{fornecedor_nome}</strong>,</p>

            <p>Temos o prazer de informar que sua proposta para a cotação <strong>{solicitacao_numero}</strong> foi <span style="color: #10b981; font-weight: bold;">ACEITA</span>!</p>

            <div class="destaque">
                <h2 style="color: #059669; margin: 0 0 10px 0;">{solicitacao_titulo}</h2>
                <p style="font-size: 24px; margin: 0; color: #059669;">Valor Total: R$ {valor_total:,.2f}</p>
            </div>

            <h3 style="color: #10b981;">Itens da Proposta Vencedora</h3>
            <table>
                <thead>
                    <tr>
                        <th style="width: 50px;">#</th>
                        <th>Produto</th>
                        <th style="width: 80px; text-align: center;">Qtd</th>
                        <th style="width: 120px; text-align: right;">Preço Unit.</th>
                        <th style="width: 120px; text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {itens_html}
                    <tr class="total">
                        <td colspan="4" style="padding: 12px; text-align: right;"><strong>TOTAL:</strong></td>
                        <td style="padding: 12px; text-align: right;"><strong>R$ {valor_total:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>

            {prazo_html}
            {condicao_html}

            <div class="proximos-passos">
                <strong>📋 Próximos Passos:</strong>
                <ul style="margin: 10px 0 0 0;">
                    <li>Em breve você receberá o <strong>Pedido de Compra</strong> oficial</li>
                    <li>Aguarde o contato do nosso departamento de compras para confirmar os detalhes</li>
                    <li>Prepare-se para o faturamento e entrega conforme acordado</li>
                </ul>
            </div>

            <p>Agradecemos pela sua participação e esperamos continuar essa parceria de sucesso!</p>

            <p>Atenciosamente,<br>
            <strong>Departamento de Compras</strong></p>
        </div>
        <div class="footer">
            <p>Este é um email automático do Sistema de Gestão de Compras</p>
            <p>Referência: {solicitacao_numero}</p>
        </div>
    </div>
</body>
</html>
"""

        # Criar versão texto dos itens
        itens_texto = ""
        for i, item in enumerate(itens, 1):
            itens_texto += f"  {i}. {item.get('produto_nome', 'N/A')} - Qtd: {item.get('quantidade', 0)} - R$ {item.get('preco_unitario', 0):,.2f} - Total: R$ {item.get('preco_total', 0):,.2f}\n"

        corpo_texto = f"""
🎉 PARABÉNS! Sua proposta foi ACEITA!

Prezado(a) {fornecedor_nome},

Temos o prazer de informar que sua proposta para a cotação {solicitacao_numero} foi ACEITA!

{solicitacao_titulo}
Valor Total: R$ {valor_total:,.2f}

ITENS DA PROPOSTA VENCEDORA:
-------------------------------------------
{itens_texto}
-------------------------------------------
TOTAL: R$ {valor_total:,.2f}

{f'Prazo de Entrega: {prazo_entrega} dias' if prazo_entrega else ''}
{f'Condição de Pagamento: {condicao_pagamento}' if condicao_pagamento else ''}

PRÓXIMOS PASSOS:
- Em breve você receberá o Pedido de Compra oficial
- Aguarde o contato do nosso departamento de compras para confirmar os detalhes
- Prepare-se para o faturamento e entrega conforme acordado

Agradecemos pela sua participação e esperamos continuar essa parceria de sucesso!

Atenciosamente,
Departamento de Compras

Referência: {solicitacao_numero}
"""

        return self.enviar_email(
            destinatario=fornecedor_email,
            assunto=assunto,
            corpo_html=corpo_html,
            corpo_texto=corpo_texto
        )


    def enviar_ordem_compra(
        self,
        fornecedor_email: str,
        fornecedor_nome: str,
        pedido_numero: str,
        itens: List[dict],
        valor_total: float,
        prazo_entrega: Optional[int] = None,
        condicao_pagamento: Optional[str] = None,
        frete_tipo: Optional[str] = None,
        observacoes: Optional[str] = None,
        empresa_nome: Optional[str] = None
    ) -> bool:
        """
        Envia email com a Ordem de Compra oficial para o fornecedor

        Args:
            fornecedor_email: Email do fornecedor
            fornecedor_nome: Nome do fornecedor
            pedido_numero: Número do pedido (ex: PC-2024-00001)
            itens: Lista de itens com produto_nome, quantidade, unidade, preco_unitario, valor_total
            valor_total: Valor total do pedido
            prazo_entrega: Prazo de entrega em dias
            condicao_pagamento: Condição de pagamento
            frete_tipo: Tipo do frete (CIF/FOB)
            observacoes: Observações do pedido
            empresa_nome: Nome da empresa compradora

        Returns:
            True se enviado com sucesso
        """
        assunto = f"[ORDEM DE COMPRA] {pedido_numero} - Pedido Oficial"

        # Criar HTML dos itens
        itens_html = ""
        for i, item in enumerate(itens, 1):
            itens_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{i}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;"><strong>{item.get('produto_nome', 'N/A')}</strong><br><small style="color: #666;">{item.get('especificacoes', '') or ''}</small></td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{item.get('quantidade', 0)} {item.get('unidade', '')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">R$ {float(item.get('preco_unitario', 0)):,.2f}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">R$ {float(item.get('valor_total', 0)):,.2f}</td>
            </tr>
            """

        prazo_html = f"<tr><td style='padding: 8px;'><strong>Prazo de Entrega:</strong></td><td style='padding: 8px;'>{prazo_entrega} dias</td></tr>" if prazo_entrega else ""
        condicao_html = f"<tr><td style='padding: 8px;'><strong>Condição de Pagamento:</strong></td><td style='padding: 8px;'>{condicao_pagamento}</td></tr>" if condicao_pagamento else ""
        frete_html = f"<tr><td style='padding: 8px;'><strong>Frete:</strong></td><td style='padding: 8px;'>{frete_tipo}</td></tr>" if frete_tipo else ""
        obs_html = f"<tr><td style='padding: 8px;'><strong>Observações:</strong></td><td style='padding: 8px;'>{observacoes}</td></tr>" if observacoes else ""
        empresa_html = empresa_nome or "Departamento de Compras"

        corpo_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .destaque {{ background: #eff6ff; border: 2px solid #2563eb; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
        th {{ background: #2563eb; color: white; padding: 12px; text-align: left; }}
        .total {{ background: #eff6ff; font-weight: bold; }}
        .info-box {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 20px 0; }}
        .importante {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">📦 ORDEM DE COMPRA</h1>
            <p style="margin: 10px 0 0 0; font-size: 24px; font-weight: bold;">{pedido_numero}</p>
        </div>
        <div class="content">
            <p>Prezado(a) <strong>{fornecedor_nome}</strong>,</p>

            <p>Segue abaixo a <strong>Ordem de Compra oficial</strong>. Por favor, confirme o recebimento e proceda conforme as condições estabelecidas.</p>

            <div class="destaque">
                <h2 style="color: #1d4ed8; margin: 0 0 10px 0;">Pedido: {pedido_numero}</h2>
                <p style="font-size: 28px; margin: 0; color: #1d4ed8;">R$ {valor_total:,.2f}</p>
            </div>

            <h3 style="color: #2563eb;">Itens do Pedido</h3>
            <table>
                <thead>
                    <tr>
                        <th style="width: 50px;">#</th>
                        <th>Produto</th>
                        <th style="width: 100px; text-align: center;">Quantidade</th>
                        <th style="width: 120px; text-align: right;">Preço Unit.</th>
                        <th style="width: 120px; text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {itens_html}
                    <tr class="total">
                        <td colspan="4" style="padding: 12px; text-align: right;"><strong>VALOR TOTAL:</strong></td>
                        <td style="padding: 12px; text-align: right;"><strong>R$ {valor_total:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>

            <div class="info-box">
                <h4 style="margin: 0 0 10px 0; color: #2563eb;">Condições do Pedido</h4>
                <table style="margin: 0; background: transparent;">
                    {prazo_html}
                    {condicao_html}
                    {frete_html}
                    {obs_html}
                </table>
            </div>

            <div class="importante">
                <strong>⚠️ IMPORTANTE:</strong>
                <ul style="margin: 10px 0 0 0;">
                    <li>Por favor, <strong>confirme o recebimento</strong> deste pedido respondendo este email</li>
                    <li>Informe a <strong>data prevista de entrega</strong></li>
                    <li>Qualquer divergência, entre em contato imediatamente</li>
                </ul>
            </div>

            <p>Contamos com sua parceria e aguardamos a confirmação.</p>

            <p>Atenciosamente,<br>
            <strong>{empresa_html}</strong></p>
        </div>
        <div class="footer">
            <p>Este é um email automático do Sistema de Gestão de Compras</p>
            <p>Referência: {pedido_numero}</p>
        </div>
    </div>
</body>
</html>
"""

        # Criar versão texto dos itens
        itens_texto = ""
        for i, item in enumerate(itens, 1):
            itens_texto += f"  {i}. {item.get('produto_nome', 'N/A')} - Qtd: {item.get('quantidade', 0)} {item.get('unidade', '')} - R$ {float(item.get('preco_unitario', 0)):,.2f} - Total: R$ {float(item.get('valor_total', 0)):,.2f}\n"

        corpo_texto = f"""
📦 ORDEM DE COMPRA - {pedido_numero}

Prezado(a) {fornecedor_nome},

Segue abaixo a Ordem de Compra oficial. Por favor, confirme o recebimento e proceda conforme as condições estabelecidas.

PEDIDO: {pedido_numero}
VALOR TOTAL: R$ {valor_total:,.2f}

ITENS DO PEDIDO:
-------------------------------------------
{itens_texto}
-------------------------------------------
VALOR TOTAL: R$ {valor_total:,.2f}

CONDIÇÕES DO PEDIDO:
{f'- Prazo de Entrega: {prazo_entrega} dias' if prazo_entrega else ''}
{f'- Condição de Pagamento: {condicao_pagamento}' if condicao_pagamento else ''}
{f'- Frete: {frete_tipo}' if frete_tipo else ''}
{f'- Observações: {observacoes}' if observacoes else ''}

⚠️ IMPORTANTE:
- Por favor, confirme o recebimento deste pedido respondendo este email
- Informe a data prevista de entrega
- Qualquer divergência, entre em contato imediatamente

Contamos com sua parceria e aguardamos a confirmação.

Atenciosamente,
{empresa_html}

Referência: {pedido_numero}
"""

        return self.enviar_email(
            destinatario=fornecedor_email,
            assunto=assunto,
            corpo_html=corpo_html,
            corpo_texto=corpo_texto
        )


# Instância singleton
email_service = EmailService()
