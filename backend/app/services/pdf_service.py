"""
Serviço de Geração de PDF com Formulários Preenchíveis
Para Solicitações de Cotação
"""
import io
from datetime import datetime
from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfform
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class PDFService:
    """Serviço para geração de PDFs com formulários preenchíveis"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos personalizados"""
        self.styles.add(ParagraphStyle(
            name='TitleBlue',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1d4ed8'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='SubtitleGray',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#059669'),
            spaceBefore=15,
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='NormalLeft',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT
        ))

    def gerar_pdf_cotacao(
        self,
        fornecedor_nome: str,
        fornecedor_cnpj: Optional[str],
        solicitacao_numero: str,
        solicitacao_titulo: str,
        itens: List[dict],
        observacoes: Optional[str] = None,
        data_limite: Optional[str] = None,
        solicitacao_id: int = 0
    ) -> bytes:
        """
        Gera PDF de solicitação de cotação com campos preenchíveis

        Args:
            fornecedor_nome: Nome do fornecedor
            fornecedor_cnpj: CNPJ do fornecedor
            solicitacao_numero: Número da solicitação
            solicitacao_titulo: Título da solicitação
            itens: Lista de itens [{produto_nome, quantidade, unidade_medida, especificacoes}]
            observacoes: Observações gerais
            data_limite: Data limite para resposta
            solicitacao_id: ID da solicitação

        Returns:
            Bytes do PDF gerado
        """
        buffer = io.BytesIO()

        # Criar canvas para desenhar o PDF com formulários
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Desenhar o PDF
        self._draw_header(c, width, height, solicitacao_numero, solicitacao_titulo)
        self._draw_fornecedor_info(c, width, height, fornecedor_nome, fornecedor_cnpj)
        y_pos = self._draw_itens_table(c, width, height, itens)
        y_pos = self._draw_form_fields(c, width, y_pos, itens)
        self._draw_footer(c, width, data_limite, solicitacao_id)

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def _draw_header(self, c: canvas.Canvas, width: float, height: float,
                     solicitacao_numero: str, solicitacao_titulo: str):
        """Desenha o cabeçalho do PDF"""
        # Fundo azul do header
        c.setFillColor(colors.HexColor('#1d4ed8'))
        c.rect(0, height - 80, width, 80, fill=True, stroke=False)

        # Título
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, height - 40, "SOLICITAÇÃO DE COTAÇÃO")

        # Número da solicitação
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, height - 60, solicitacao_numero)

        # Título da solicitação
        c.setFillColor(colors.HexColor('#333333'))
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 100, solicitacao_titulo)

        # Data de emissão
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor('#666666'))
        data_hoje = datetime.now().strftime('%d/%m/%Y às %H:%M')
        c.drawRightString(width - 20, height - 95, f"Emitido em: {data_hoje}")

    def _draw_fornecedor_info(self, c: canvas.Canvas, width: float, height: float,
                              fornecedor_nome: str, fornecedor_cnpj: Optional[str]):
        """Desenha informações do fornecedor"""
        y = height - 130

        # Box do fornecedor
        c.setStrokeColor(colors.HexColor('#e5e7eb'))
        c.setFillColor(colors.HexColor('#f9fafb'))
        c.roundRect(20, y - 50, width - 40, 50, 5, fill=True, stroke=True)

        c.setFillColor(colors.HexColor('#333333'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, y - 20, "FORNECEDOR:")

        c.setFont("Helvetica", 10)
        c.drawString(110, y - 20, fornecedor_nome)

        if fornecedor_cnpj:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(30, y - 38, "CNPJ:")
            c.setFont("Helvetica", 10)
            c.drawString(70, y - 38, fornecedor_cnpj)

    def _draw_itens_table(self, c: canvas.Canvas, width: float, height: float,
                          itens: List[dict]) -> float:
        """Desenha a tabela de itens solicitados"""
        y = height - 200

        # Título da seção
        c.setFillColor(colors.HexColor('#059669'))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20, y, "ITENS SOLICITADOS")

        y -= 25

        # Cabeçalho da tabela
        c.setFillColor(colors.HexColor('#3b82f6'))
        c.rect(20, y - 20, width - 40, 20, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25, y - 15, "#")
        c.drawString(45, y - 15, "Produto")
        c.drawString(width - 140, y - 15, "Qtd")
        c.drawString(width - 80, y - 15, "Unid")

        y -= 25

        # Linhas dos itens
        c.setFillColor(colors.HexColor('#333333'))
        c.setFont("Helvetica", 9)

        for i, item in enumerate(itens, 1):
            # Alternar cor de fundo
            if i % 2 == 0:
                c.setFillColor(colors.HexColor('#f3f4f6'))
                c.rect(20, y - 15, width - 40, 18, fill=True, stroke=False)

            c.setFillColor(colors.HexColor('#333333'))
            c.drawString(25, y - 10, str(i))

            # Truncar nome do produto se muito longo
            produto_nome = item.get('produto_nome', 'N/A')
            if len(produto_nome) > 50:
                produto_nome = produto_nome[:47] + "..."
            c.drawString(45, y - 10, produto_nome)

            c.drawString(width - 140, y - 10, str(item.get('quantidade', 0)))
            c.drawString(width - 80, y - 10, item.get('unidade_medida', 'UN'))

            # Especificações em linha menor
            if item.get('especificacoes'):
                y -= 12
                c.setFont("Helvetica-Oblique", 8)
                c.setFillColor(colors.HexColor('#666666'))
                esp = item['especificacoes']
                if len(esp) > 80:
                    esp = esp[:77] + "..."
                c.drawString(45, y - 10, f"Obs: {esp}")
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.HexColor('#333333'))

            y -= 20

        return y - 20

    def _draw_form_fields(self, c: canvas.Canvas, width: float, y_start: float,
                          itens: List[dict]) -> float:
        """Desenha os campos de formulário preenchíveis"""
        y = y_start

        # Título da seção
        c.setFillColor(colors.HexColor('#059669'))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20, y, "PREENCHA SUA PROPOSTA")

        y -= 10

        # Box verde claro
        box_height = 30 + (len(itens) * 25) + 130
        c.setStrokeColor(colors.HexColor('#10b981'))
        c.setFillColor(colors.HexColor('#ecfdf5'))
        c.roundRect(20, y - box_height, width - 40, box_height, 5, fill=True, stroke=True)

        y -= 25

        # Instruções
        c.setFillColor(colors.HexColor('#065f46'))
        c.setFont("Helvetica", 9)
        c.drawString(30, y, "Preencha os campos abaixo com seus valores. Os campos em branco são editáveis.")

        y -= 25

        # Tabela de preços (com campos preenchíveis)
        # Cabeçalho
        c.setFillColor(colors.HexColor('#10b981'))
        c.rect(30, y - 18, width - 60, 18, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(35, y - 13, "Produto")
        c.drawString(width - 220, y - 13, "Qtd")
        c.drawString(width - 170, y - 13, "Preço Unit. (R$)")
        c.drawString(width - 85, y - 13, "Total (R$)")

        y -= 22

        # Campos para cada item
        for i, item in enumerate(itens):
            c.setFillColor(colors.HexColor('#333333'))
            c.setFont("Helvetica", 9)

            produto_nome = item.get('produto_nome', 'N/A')
            if len(produto_nome) > 35:
                produto_nome = produto_nome[:32] + "..."
            c.drawString(35, y - 12, produto_nome)
            c.drawString(width - 220, y - 12, str(item.get('quantidade', 0)))

            # Campo preenchível: Preço Unitário
            c.setFillColor(colors.HexColor('#fffef0'))
            c.rect(width - 175, y - 18, 70, 18, fill=True, stroke=True)
            form = c.acroForm
            form.textfield(
                name=f'preco_unit_{i}',
                tooltip=f'Preço unitário para {produto_nome}',
                x=width - 173,
                y=y - 16,
                width=66,
                height=14,
                borderWidth=0,
                fillColor=colors.HexColor('#fffef0'),
                textColor=colors.black,
                fontSize=9,
                fieldFlags='',
            )

            # Campo preenchível: Total
            c.setFillColor(colors.HexColor('#fffef0'))
            c.rect(width - 90, y - 18, 60, 18, fill=True, stroke=True)
            form.textfield(
                name=f'total_{i}',
                tooltip=f'Total para {produto_nome}',
                x=width - 88,
                y=y - 16,
                width=56,
                height=14,
                borderWidth=0,
                fillColor=colors.HexColor('#fffef0'),
                textColor=colors.black,
                fontSize=9,
                fieldFlags='',
            )

            y -= 25

        y -= 15

        # Campos gerais
        campos_gerais = [
            ('prazo_entrega', 'Prazo de Entrega (dias):', 80),
            ('condicoes_pagamento', 'Condições de Pagamento:', 200),
            ('frete', 'Frete (CIF/FOB e valor):', 200),
            ('validade', 'Validade da Proposta (dias):', 80),
            ('observacoes', 'Observações:', 300),
        ]

        for campo_id, label, campo_width in campos_gerais:
            c.setFillColor(colors.HexColor('#333333'))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(35, y - 12, label)

            # Campo preenchível
            label_width = c.stringWidth(label, "Helvetica-Bold", 9)
            c.setFillColor(colors.HexColor('#fffef0'))
            c.rect(40 + label_width, y - 18, campo_width, 18, fill=True, stroke=True)

            form = c.acroForm
            form.textfield(
                name=campo_id,
                tooltip=label,
                x=42 + label_width,
                y=y - 16,
                width=campo_width - 4,
                height=14,
                borderWidth=0,
                fillColor=colors.HexColor('#fffef0'),
                textColor=colors.black,
                fontSize=9,
                fieldFlags='',
            )

            y -= 22

        return y - 20

    def _draw_footer(self, c: canvas.Canvas, width: float, data_limite: Optional[str],
                     solicitacao_id: int):
        """Desenha o rodapé do PDF"""
        # Box de importante
        c.setStrokeColor(colors.HexColor('#f59e0b'))
        c.setFillColor(colors.HexColor('#fef3c7'))
        c.roundRect(20, 60, width - 40, 60, 5, fill=True, stroke=True)

        c.setFillColor(colors.HexColor('#92400e'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, 105, "IMPORTANTE:")

        c.setFont("Helvetica", 9)
        c.drawString(30, 90, "• Preencha todos os campos e salve o PDF")
        c.drawString(30, 77, "• Responda o email anexando este PDF preenchido")
        if data_limite:
            c.drawString(280, 90, f"• Prazo para resposta: {data_limite}")

        # Rodapé
        c.setFillColor(colors.HexColor('#666666'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 40, "Sistema de Gestão de Compras")
        c.drawCentredString(width / 2, 28, f"Referência: {solicitacao_id}")


# Instância singleton
pdf_service = PDFService()
