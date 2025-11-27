"""
Script de teste para verificar o template de email de cotação
"""
import sys
import os

# Adicionar o diretório do backend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.email_service import EmailService

def test_template():
    """Gera o HTML do template e salva em arquivo para visualização"""

    service = EmailService()

    # Simular dados de uma cotação
    prazo = "02/12/2025"
    fornecedor_nome = "Fornecedor Teste"
    solicitacao_numero = "SC-2025-00003"
    solicitacao_titulo = "Teste de Template"
    solicitacao_id = 999

    itens = [
        {
            'produto_nome': 'Disco Diamantado 110mm',
            'quantidade': 10,
            'unidade_medida': 'UN',
            'especificacoes': 'Para corte de granito'
        },
        {
            'produto_nome': 'Impermeabilizante para Pedras',
            'quantidade': 5,
            'unidade_medida': 'L',
            'especificacoes': ''
        }
    ]

    # Criar HTML dos itens (tabela de visualização)
    itens_html = ""
    itens_preenchimento_html = ""
    itens_texto = ""
    itens_preenchimento_texto = ""

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
        # Tabela de preenchimento
        itens_preenchimento_html += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;">{item.get('produto_nome', 'N/A')}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{item.get('quantidade', 0)}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center; background: #fffef0;">R$ _______</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center; background: #fffef0;">R$ _______</td>
        </tr>
        """
        especificacoes_texto = f" ({item.get('especificacoes', '')})" if item.get('especificacoes') else ""
        itens_texto += f"  {i}. {item.get('produto_nome', 'N/A')} - {item.get('quantidade', 0)} {item.get('unidade_medida', 'UN')}{especificacoes_texto}\n"
        itens_preenchimento_texto += f"  {item.get('produto_nome', 'N/A')} | Qtd: {item.get('quantidade', 0)} | Preco Unit: R$ _____ | Total: R$ _____\n"

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
                        {itens_preenchimento_html}
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
            <p>Referência: {solicitacao_numero} | ID: {solicitacao_id}</p>
        </div>
    </div>
</body>
</html>
"""

    # Salvar HTML para visualização
    output_path = os.path.join(os.path.dirname(__file__), 'template_preview.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(corpo_html)

    print(f"Template salvo em: {output_path}")
    print("\n=== VERIFICANDO SE O TEMPLATE CONTÉM A SEÇÃO DE PREENCHIMENTO ===")

    if "PREENCHA SUA PROPOSTA ABAIXO" in corpo_html:
        print("✅ Template contém seção de preenchimento")
    else:
        print("❌ Template NÃO contém seção de preenchimento")

    if "R$ _______" in corpo_html:
        print("✅ Template contém campos R$ _______")
    else:
        print("❌ Template NÃO contém campos R$ _______")

    if "#4caf50" in corpo_html:
        print("✅ Template contém cor verde (#4caf50)")
    else:
        print("❌ Template NÃO contém cor verde")

    print("\n=== ABRA O ARQUIVO template_preview.html NO NAVEGADOR PARA VISUALIZAR ===")

    return corpo_html

if __name__ == "__main__":
    test_template()
