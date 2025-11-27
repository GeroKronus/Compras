"""
Servico de IA usando Claude (Anthropic)
Analisa propostas e sugere a melhor opcao
Com controle de uso por tenant
"""
import json
from typing import Optional
from anthropic import Anthropic
from app.config import settings


class AIService:
    """Servico para analise de propostas com IA"""

    MODEL = "claude-sonnet-4-20250514"

    def __init__(self):
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    @property
    def is_available(self) -> bool:
        """Verifica se a IA esta disponivel"""
        return self.client is not None

    def get_client_for_tenant(self, db, tenant_id: int) -> Optional[Anthropic]:
        """
        Obtem cliente Anthropic para o tenant.
        Usa chave propria se configurada, senao usa a da aplicacao.
        """
        from app.services.ia_usage_service import ia_usage_service

        chave, e_propria = ia_usage_service.obter_chave_api(db, tenant_id)

        if not chave:
            return None

        return Anthropic(api_key=chave)

    def analisar_propostas(
        self,
        solicitacao: dict,
        propostas: list[dict],
        criterios: Optional[dict] = None
    ) -> dict:
        """
        Analisa propostas e sugere a melhor opcao

        Args:
            solicitacao: Dados da solicitacao de cotacao
            propostas: Lista de propostas com seus itens
            criterios: Pesos personalizados (preco, prazo, condicoes)

        Returns:
            Dict com sugestao, motivos e alertas
        """
        if not self.is_available:
            return {"error": "API da Anthropic nao configurada"}

        if len(propostas) < 2:
            return {"error": "Necessario pelo menos 2 propostas para analise"}

        # Montar prompt
        prompt = self._montar_prompt(solicitacao, propostas, criterios)

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                system="""Voce e um especialista em compras corporativas e analise de propostas.
                Sua funcao e analisar propostas de fornecedores e recomendar a melhor opcao.
                Sempre responda em JSON valido no formato especificado.
                Seja objetivo e justifique suas recomendacoes com dados concretos."""
            )

            # Extrair resposta
            content = response.content[0].text

            # Tentar parsear JSON
            try:
                # Remover markdown se houver
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                resultado = json.loads(content.strip())
                return resultado
            except json.JSONDecodeError:
                # Se nao conseguir parsear, retornar texto bruto
                return {
                    "proposta_sugerida_id": propostas[0]["id"],
                    "analise_texto": content,
                    "motivos": ["Analise disponivel em texto"],
                    "alertas": []
                }

        except Exception as e:
            return {"error": f"Erro ao consultar IA: {str(e)}"}

    def _montar_prompt(
        self,
        solicitacao: dict,
        propostas: list[dict],
        criterios: Optional[dict] = None
    ) -> str:
        """Monta o prompt para analise"""

        criterios = criterios or {
            "peso_preco": 50,
            "peso_prazo": 30,
            "peso_condicoes": 20
        }

        prompt = f"""
Analise as seguintes propostas para a solicitacao de cotacao e recomende a melhor opcao.

## SOLICITACAO
- Numero: {solicitacao.get('numero', 'N/A')}
- Titulo: {solicitacao.get('titulo', 'N/A')}
- Urgente: {'Sim' if solicitacao.get('urgente') else 'Nao'}
- Prazo desejado: {solicitacao.get('prazo_entrega_desejado', 'N/A')} dias
- Condicoes desejadas: {solicitacao.get('condicoes_pagamento_desejadas', 'N/A')}

## CRITERIOS DE AVALIACAO
- Preco: {criterios['peso_preco']}%
- Prazo de entrega: {criterios['peso_prazo']}%
- Condicoes de pagamento: {criterios['peso_condicoes']}%

## PROPOSTAS

"""
        for i, proposta in enumerate(propostas, 1):
            prompt += f"""
### Proposta {i} - {proposta.get('fornecedor_nome', 'Fornecedor')} (ID: {proposta['id']})
- Valor Total: R$ {proposta.get('valor_total', 0):,.2f}
- Prazo de Entrega: {proposta.get('prazo_entrega', 'N/A')} dias
- Condicoes de Pagamento: {proposta.get('condicoes_pagamento', 'N/A')}
- Frete: {proposta.get('frete_tipo', 'N/A')} - R$ {proposta.get('frete_valor', 0):,.2f}
- Validade: {proposta.get('validade_proposta', 'N/A')}

Itens:
"""
            for item in proposta.get('itens', []):
                prompt += f"""  - {item.get('produto_nome', 'Produto')}: R$ {item.get('preco_unitario', 0):,.2f}/un (Qtd: {item.get('quantidade_disponivel', 'N/A')}, Desconto: {item.get('desconto_percentual', 0)}%)
"""

        prompt += """

## INSTRUCOES
Analise todas as propostas considerando os criterios de avaliacao e responda APENAS com um JSON valido no seguinte formato:

{
    "proposta_sugerida_id": <ID da proposta recomendada>,
    "fornecedor_nome": "<Nome do fornecedor>",
    "score_total": <nota de 0 a 5>,
    "scores": {
        "preco": <nota de 0 a 5>,
        "prazo": <nota de 0 a 5>,
        "condicoes": <nota de 0 a 5>
    },
    "motivos": [
        "<motivo 1>",
        "<motivo 2>",
        "<motivo 3>"
    ],
    "economia_estimada": <valor em R$ comparado a segunda melhor>,
    "alertas": [
        "<alerta 1 se houver>",
        "<alerta 2 se houver>"
    ],
    "comparativo_resumido": "<texto resumido comparando as propostas>"
}
"""
        return prompt


    def extrair_dados_proposta_email(self, corpo_email: str, conteudo_anexo: str = None) -> dict:
        """
        Extrai dados de proposta de um email usando Claude.

        IMPORTANTE: Este metodo PRESUME que todo email de resposta de um fornecedor
        e uma proposta comercial. A IA deve ser AGRESSIVA na extracao de dados,
        mesmo que o fornecedor tenha escrito a mao em um guardanapo.

        Args:
            corpo_email: Texto do corpo do email
            conteudo_anexo: Texto extraido de anexos PDF (opcional)

        Returns:
            Dict com dados extraidos (preco, prazo, condicoes, etc)
        """
        if not self.is_available:
            return {"error": "API da Anthropic nao configurada"}

        # Combinar corpo do email com anexo se houver
        conteudo_completo = corpo_email or ""
        if conteudo_anexo:
            conteudo_completo += f"\n\n=== CONTEUDO DO ANEXO PDF ===\n{conteudo_anexo}"

        prompt = f"""
VOCE E UM ESPECIALISTA EM EXTRAIR DADOS DE PROPOSTAS COMERCIAIS.

Este email e uma RESPOSTA de um FORNECEDOR a uma solicitacao de cotacao.
PRESUMA que este email CONTEM uma proposta comercial, mesmo que esteja mal formatado.

O fornecedor pode ter respondido de diversas formas:
- Digitando os valores diretamente no email
- Anexando um PDF com a proposta
- Escrevendo de forma informal ("te faço por 50 reais", "entrego semana que vem")
- Usando abreviacoes ("pgto 30dd", "ent. imediata", "R$15/un")
- Misturando a resposta com a citacao do email original

SUA MISSAO: Encontrar e extrair TODOS os dados comerciais possiveis.

## CONTEUDO DO EMAIL E ANEXOS
{conteudo_completo}

## REGRAS DE EXTRACAO

1. PRECOS: Procure por qualquer valor monetario (R$, reais, $, "por X", "a X", "valor:", "preco:")
   - Se encontrar "R$ 12,50" ou "12.50" ou "12,5" -> preco_unitario: 12.5
   - Se encontrar "total de R$ 100" -> preco_total: 100
   - Converta virgula para ponto decimal

2. PRAZOS: Procure por indicacoes de tempo de entrega
   - "entrega imediata", "pronta entrega" -> prazo_entrega_dias: 0
   - "5 dias", "5d", "5 dias uteis" -> prazo_entrega_dias: 5
   - "1 semana" -> prazo_entrega_dias: 7
   - "15 dias", "quinze dias" -> prazo_entrega_dias: 15

3. PAGAMENTO: Procure por condicoes de pagamento
   - "30 dias", "30dd", "30/60/90" -> condicoes_pagamento: "30 dias"
   - "a vista", "avista" -> condicoes_pagamento: "a vista"
   - "boleto", "pix", "cartao" -> inclua na condicao

4. FRETE: Procure por informacoes de frete
   - "frete gratis", "frete incluso", "CIF" -> frete_incluso: true
   - "frete por conta", "FOB", "+ frete" -> frete_incluso: false
   - "frete R$ 50" -> frete_valor: 50

5. MARCA/PRODUTO: Procure por marcas ou especificacoes
   - Nome de fabricantes, modelos, referencias

6. IGNORE a parte do email que e citacao do email original (geralmente apos "---" ou ">")

Responda APENAS com JSON valido:

{{
    "preco_unitario": <numero ou null>,
    "preco_total": <numero ou null>,
    "quantidade": <numero ou null>,
    "prazo_entrega_dias": <numero ou null>,
    "condicoes_pagamento": "<texto ou null>",
    "frete_incluso": <true/false/null>,
    "frete_valor": <numero ou null>,
    "validade_proposta": "<texto ou null>",
    "marca_produto": "<texto ou null>",
    "observacoes": "<informacoes adicionais encontradas>",
    "confianca_extracao": <0-100>
}}

IMPORTANTE:
- NAO retorne null para preco se encontrar QUALQUER valor monetario no email
- Se o email tiver algum conteudo de resposta do fornecedor, a confianca deve ser >= 50
- Seja AGRESSIVO na extracao - e melhor extrair algo errado do que perder dados
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                system="Voce e um assistente AGRESSIVO na extracao de dados comerciais. Sua missao e encontrar precos, prazos e condicoes em qualquer formato. NUNCA diga que nao encontrou dados se houver qualquer indicacao de valores no texto."
            )

            content = response.content[0].text

            # Parsear JSON
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                return json.loads(content.strip())
            except json.JSONDecodeError:
                return {
                    "texto_bruto": content,
                    "confianca_extracao": 0
                }

        except Exception as e:
            return {"error": f"Erro ao extrair dados: {str(e)}"}

    def analisar_propostas_com_registro(
        self,
        db,
        tenant_id: int,
        solicitacao: dict,
        propostas: list[dict],
        criterios: Optional[dict] = None,
        usuario_id: Optional[int] = None
    ) -> dict:
        """
        Analisa propostas e registra o uso da IA.
        Versao com controle de uso por tenant.
        """
        from app.services.ia_usage_service import ia_usage_service

        # Verificar limite
        pode_usar, mensagem, _ = ia_usage_service.verificar_limite(db, tenant_id)
        if not pode_usar:
            return {"error": mensagem}

        # Obter cliente para o tenant
        client = self.get_client_for_tenant(db, tenant_id)
        if not client:
            return {"error": "API da Anthropic nao configurada"}

        if len(propostas) < 2:
            return {"error": "Necessario pelo menos 2 propostas para analise"}

        prompt = self._montar_prompt(solicitacao, propostas, criterios)

        try:
            response = client.messages.create(
                model=self.MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                system="""Voce e um especialista em compras corporativas e analise de propostas.
                Sua funcao e analisar propostas de fornecedores e recomendar a melhor opcao.
                Sempre responda em JSON valido no formato especificado.
                Seja objetivo e justifique suas recomendacoes com dados concretos."""
            )

            # Registrar uso
            ia_usage_service.registrar_uso(
                db=db,
                tenant_id=tenant_id,
                tipo_operacao="analise_proposta",
                modelo=self.MODEL,
                tokens_entrada=response.usage.input_tokens,
                tokens_saida=response.usage.output_tokens,
                referencia_id=solicitacao.get('id'),
                referencia_tipo="solicitacao",
                descricao=f"Analise de {len(propostas)} propostas",
                usuario_id=usuario_id
            )

            content = response.content[0].text

            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                return json.loads(content.strip())
            except json.JSONDecodeError:
                return {
                    "proposta_sugerida_id": propostas[0]["id"],
                    "analise_texto": content,
                    "motivos": ["Analise disponivel em texto"],
                    "alertas": []
                }

        except Exception as e:
            return {"error": f"Erro ao consultar IA: {str(e)}"}

    def extrair_dados_email_com_registro(
        self,
        db,
        tenant_id: int,
        corpo_email: str,
        email_id: Optional[int] = None,
        usuario_id: Optional[int] = None
    ) -> dict:
        """
        Extrai dados de email e registra o uso da IA.
        Versao com controle de uso por tenant.
        """
        from app.services.ia_usage_service import ia_usage_service

        # Verificar limite
        pode_usar, mensagem, _ = ia_usage_service.verificar_limite(db, tenant_id)
        if not pode_usar:
            return {"error": mensagem}

        # Obter cliente para o tenant
        client = self.get_client_for_tenant(db, tenant_id)
        if not client:
            return {"error": "API da Anthropic nao configurada"}

        prompt = f"""
Analise o seguinte email de resposta a uma solicitacao de cotacao e extraia os dados da proposta.

## EMAIL RECEBIDO
{corpo_email}

## INSTRUCOES
Extraia os dados da proposta e responda APENAS com um JSON valido no seguinte formato:

{{
    "preco_unitario": <valor numerico ou null se nao encontrado>,
    "preco_total": <valor numerico ou null>,
    "quantidade": <numero ou null>,
    "prazo_entrega_dias": <numero de dias ou null>,
    "condicoes_pagamento": "<texto das condicoes ou null>",
    "frete_incluso": <true/false ou null>,
    "frete_valor": <valor do frete ou null>,
    "validade_proposta": "<data ou dias de validade ou null>",
    "marca_produto": "<marca oferecida ou null>",
    "observacoes": "<outras informacoes relevantes>",
    "confianca_extracao": <0 a 100 - nivel de confianca nos dados extraidos>
}}

Se algum dado nao estiver claro no email, use null.
"""

        try:
            response = client.messages.create(
                model=self.MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                system="Voce e um assistente especializado em extrair dados estruturados de emails comerciais. Sempre responda em JSON valido."
            )

            # Registrar uso
            ia_usage_service.registrar_uso(
                db=db,
                tenant_id=tenant_id,
                tipo_operacao="extracao_email",
                modelo=self.MODEL,
                tokens_entrada=response.usage.input_tokens,
                tokens_saida=response.usage.output_tokens,
                referencia_id=email_id,
                referencia_tipo="email",
                descricao="Extracao de dados de proposta",
                usuario_id=usuario_id
            )

            content = response.content[0].text

            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                return json.loads(content.strip())
            except json.JSONDecodeError:
                return {
                    "texto_bruto": content,
                    "confianca_extracao": 0
                }

        except Exception as e:
            return {"error": f"Erro ao extrair dados: {str(e)}"}


# Instancia global
ai_service = AIService()
