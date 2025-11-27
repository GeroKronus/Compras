"""
Servico de controle de uso da IA
Registra chamadas, verifica limites e gerencia creditos
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.uso_ia import UsoIA, LimiteIATenant
from app.models.tenant import Tenant

# Precos da Anthropic (por milhao de tokens) - Claude Sonnet 4
PRECOS_TOKENS = {
    "claude-sonnet-4-20250514": {
        "entrada": Decimal("3.00"),   # $3/M tokens entrada
        "saida": Decimal("15.00")     # $15/M tokens saida
    },
    "default": {
        "entrada": Decimal("3.00"),
        "saida": Decimal("15.00")
    }
}


class IAUsageService:
    """Servico para controle de uso da IA"""

    def verificar_limite(
        self,
        db: Session,
        tenant_id: int
    ) -> Tuple[bool, str, dict]:
        """
        Verifica se o tenant pode fazer mais chamadas a IA.

        Returns:
            Tupla (pode_usar, mensagem, uso_atual)
        """
        limite = self._obter_ou_criar_limite(db, tenant_id)

        # Verificar se mudou de mes
        mes_atual = datetime.now().strftime("%Y-%m")
        if limite.mes_referencia != mes_atual:
            # Resetar contadores
            limite.tokens_usados_mes = 0
            limite.chamadas_usadas_mes = 0
            limite.custo_usado_mes = Decimal("0")
            limite.mes_referencia = mes_atual
            db.commit()

        uso_atual = {
            "tokens_usados": limite.tokens_usados_mes,
            "tokens_limite": limite.tokens_mensais_limite,
            "chamadas_usadas": limite.chamadas_usadas_mes,
            "chamadas_limite": limite.chamadas_mensais_limite,
            "custo_usado": float(limite.custo_usado_mes),
            "custo_limite": float(limite.custo_mensal_limite),
            "percentual_tokens": round(limite.tokens_usados_mes / limite.tokens_mensais_limite * 100, 1) if limite.tokens_mensais_limite > 0 else 0,
            "percentual_chamadas": round(limite.chamadas_usadas_mes / limite.chamadas_mensais_limite * 100, 1) if limite.chamadas_mensais_limite > 0 else 0,
            "percentual_custo": round(float(limite.custo_usado_mes) / float(limite.custo_mensal_limite) * 100, 1) if limite.custo_mensal_limite > 0 else 0
        }

        # Verificar limites
        if limite.chamadas_usadas_mes >= limite.chamadas_mensais_limite:
            return (False, "Limite de chamadas mensais atingido", uso_atual)

        if limite.tokens_usados_mes >= limite.tokens_mensais_limite:
            return (False, "Limite de tokens mensais atingido", uso_atual)

        if limite.custo_usado_mes >= limite.custo_mensal_limite:
            return (False, "Limite de custo mensal atingido", uso_atual)

        return (True, "OK", uso_atual)

    def registrar_uso(
        self,
        db: Session,
        tenant_id: int,
        tipo_operacao: str,
        modelo: str,
        tokens_entrada: int,
        tokens_saida: int,
        referencia_id: Optional[int] = None,
        referencia_tipo: Optional[str] = None,
        descricao: Optional[str] = None,
        usuario_id: Optional[int] = None
    ) -> UsoIA:
        """
        Registra uma chamada a IA.

        Args:
            db: Sessao do banco
            tenant_id: ID do tenant
            tipo_operacao: Tipo da operacao (analise_proposta, extracao_email, etc)
            modelo: Modelo usado (claude-sonnet-4-20250514)
            tokens_entrada: Tokens de entrada
            tokens_saida: Tokens de saida
            referencia_id: ID do objeto relacionado
            referencia_tipo: Tipo do objeto (solicitacao, email)
            descricao: Descricao da operacao
            usuario_id: ID do usuario que disparou

        Returns:
            Registro de uso criado
        """
        tokens_total = tokens_entrada + tokens_saida
        custo = self._calcular_custo(modelo, tokens_entrada, tokens_saida)

        # Criar registro de uso
        uso = UsoIA(
            tenant_id=tenant_id,
            tipo_operacao=tipo_operacao,
            modelo=modelo,
            tokens_entrada=tokens_entrada,
            tokens_saida=tokens_saida,
            tokens_total=tokens_total,
            custo_estimado=custo,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            descricao=descricao,
            usuario_id=usuario_id
        )
        db.add(uso)

        # Atualizar limites do tenant
        limite = self._obter_ou_criar_limite(db, tenant_id)

        # Verificar se mudou de mes
        mes_atual = datetime.now().strftime("%Y-%m")
        if limite.mes_referencia != mes_atual:
            limite.tokens_usados_mes = 0
            limite.chamadas_usadas_mes = 0
            limite.custo_usado_mes = Decimal("0")
            limite.mes_referencia = mes_atual

        limite.tokens_usados_mes += tokens_total
        limite.chamadas_usadas_mes += 1
        limite.custo_usado_mes += custo

        db.commit()
        db.refresh(uso)

        return uso

    def _calcular_custo(
        self,
        modelo: str,
        tokens_entrada: int,
        tokens_saida: int
    ) -> Decimal:
        """Calcula custo estimado da chamada"""
        precos = PRECOS_TOKENS.get(modelo, PRECOS_TOKENS["default"])

        custo_entrada = (Decimal(tokens_entrada) / Decimal("1000000")) * precos["entrada"]
        custo_saida = (Decimal(tokens_saida) / Decimal("1000000")) * precos["saida"]

        return custo_entrada + custo_saida

    def _obter_ou_criar_limite(
        self,
        db: Session,
        tenant_id: int
    ) -> LimiteIATenant:
        """Obtem ou cria registro de limite para o tenant"""
        limite = db.query(LimiteIATenant).filter(
            LimiteIATenant.tenant_id == tenant_id
        ).first()

        if not limite:
            limite = LimiteIATenant(
                tenant_id=tenant_id,
                mes_referencia=datetime.now().strftime("%Y-%m")
            )
            db.add(limite)
            db.flush()

        return limite

    def obter_estatisticas_mes(
        self,
        db: Session,
        tenant_id: int,
        mes: Optional[str] = None
    ) -> dict:
        """
        Obtem estatisticas de uso do mes.

        Args:
            db: Sessao do banco
            tenant_id: ID do tenant
            mes: Mes no formato "YYYY-MM" (padrao: mes atual)

        Returns:
            Dict com estatisticas detalhadas
        """
        if not mes:
            mes = datetime.now().strftime("%Y-%m")

        ano, mes_num = map(int, mes.split("-"))

        # Buscar registros do mes
        registros = db.query(UsoIA).filter(
            UsoIA.tenant_id == tenant_id,
            extract('year', UsoIA.created_at) == ano,
            extract('month', UsoIA.created_at) == mes_num
        ).all()

        # Agrupar por tipo de operacao
        por_tipo = {}
        for reg in registros:
            if reg.tipo_operacao not in por_tipo:
                por_tipo[reg.tipo_operacao] = {
                    "chamadas": 0,
                    "tokens": 0,
                    "custo": Decimal("0")
                }
            por_tipo[reg.tipo_operacao]["chamadas"] += 1
            por_tipo[reg.tipo_operacao]["tokens"] += reg.tokens_total
            por_tipo[reg.tipo_operacao]["custo"] += reg.custo_estimado

        # Converter Decimal para float
        for tipo in por_tipo:
            por_tipo[tipo]["custo"] = float(por_tipo[tipo]["custo"])

        # Totais
        total_chamadas = len(registros)
        total_tokens = sum(r.tokens_total for r in registros)
        total_custo = sum(r.custo_estimado for r in registros)

        # Limites
        limite = self._obter_ou_criar_limite(db, tenant_id)

        return {
            "mes": mes,
            "total_chamadas": total_chamadas,
            "total_tokens": total_tokens,
            "total_custo": float(total_custo),
            "por_tipo": por_tipo,
            "limites": {
                "tokens_limite": limite.tokens_mensais_limite,
                "chamadas_limite": limite.chamadas_mensais_limite,
                "custo_limite": float(limite.custo_mensal_limite),
                "tokens_disponivel": max(0, limite.tokens_mensais_limite - total_tokens),
                "chamadas_disponivel": max(0, limite.chamadas_mensais_limite - total_chamadas),
                "custo_disponivel": float(max(Decimal("0"), limite.custo_mensal_limite - total_custo))
            },
            "percentuais": {
                "tokens": round(total_tokens / limite.tokens_mensais_limite * 100, 1) if limite.tokens_mensais_limite > 0 else 0,
                "chamadas": round(total_chamadas / limite.chamadas_mensais_limite * 100, 1) if limite.chamadas_mensais_limite > 0 else 0,
                "custo": round(float(total_custo) / float(limite.custo_mensal_limite) * 100, 1) if limite.custo_mensal_limite > 0 else 0
            }
        }

    def atualizar_limites(
        self,
        db: Session,
        tenant_id: int,
        tokens_limite: Optional[int] = None,
        chamadas_limite: Optional[int] = None,
        custo_limite: Optional[Decimal] = None,
        chave_propria: Optional[str] = None,
        usar_chave_propria: Optional[bool] = None
    ) -> LimiteIATenant:
        """Atualiza limites do tenant"""
        limite = self._obter_ou_criar_limite(db, tenant_id)

        if tokens_limite is not None:
            limite.tokens_mensais_limite = tokens_limite
        if chamadas_limite is not None:
            limite.chamadas_mensais_limite = chamadas_limite
        if custo_limite is not None:
            limite.custo_mensal_limite = custo_limite
        if chave_propria is not None:
            limite.chave_api_propria = chave_propria
        if usar_chave_propria is not None:
            limite.usar_chave_propria = usar_chave_propria

        db.commit()
        db.refresh(limite)

        return limite

    def obter_chave_api(
        self,
        db: Session,
        tenant_id: int
    ) -> Tuple[str, bool]:
        """
        Obtem a chave API a ser usada para o tenant.

        Returns:
            Tupla (chave_api, e_propria)
        """
        from app.config import settings

        limite = self._obter_ou_criar_limite(db, tenant_id)

        if limite.usar_chave_propria and limite.chave_api_propria:
            return (limite.chave_api_propria, True)

        return (settings.ANTHROPIC_API_KEY, False)


# Instancia global
ia_usage_service = IAUsageService()
