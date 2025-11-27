"""
Servico de Ranking de Fornecedores
Calcula e atualiza ranking baseado em tempo de resposta e performance
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.cotacao import (
    SolicitacaoCotacao, PropostaFornecedor, StatusSolicitacao, StatusProposta
)
from app.models.fornecedor import Fornecedor


class FornecedorRankingService:
    """Servico para calcular ranking de fornecedores"""

    def verificar_solicitacao_respondida(
        self,
        db: Session,
        solicitacao_id: int
    ) -> dict:
        """
        Verifica se uma solicitacao foi completamente respondida.

        Uma solicitacao e considerada respondida quando:
        - Todas as propostas tem status diferente de PENDENTE
        - Ou a data_limite_proposta foi ultrapassada

        Args:
            db: Sessao do banco
            solicitacao_id: ID da solicitacao

        Returns:
            Dict com status da verificacao
        """
        solicitacao = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.id == solicitacao_id
        ).first()

        if not solicitacao:
            return {"error": "Solicitacao nao encontrada"}

        # Buscar todas as propostas
        propostas = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id
        ).all()

        if not propostas:
            return {
                "solicitacao_id": solicitacao_id,
                "total_propostas": 0,
                "respondidas": 0,
                "pendentes": 0,
                "todas_respondidas": False,
                "prazo_expirado": self._prazo_expirou(solicitacao),
                "pode_finalizar": False
            }

        # Contar status
        pendentes = sum(1 for p in propostas if p.status == StatusProposta.PENDENTE)
        respondidas = len(propostas) - pendentes

        prazo_expirado = self._prazo_expirou(solicitacao)
        todas_respondidas = pendentes == 0

        return {
            "solicitacao_id": solicitacao_id,
            "total_propostas": len(propostas),
            "respondidas": respondidas,
            "pendentes": pendentes,
            "todas_respondidas": todas_respondidas,
            "prazo_expirado": prazo_expirado,
            "pode_finalizar": todas_respondidas or prazo_expirado,
            "detalhes_propostas": [
                {
                    "proposta_id": p.id,
                    "fornecedor_id": p.fornecedor_id,
                    "status": p.status.value,
                    "tempo_resposta_horas": self._calcular_tempo_resposta_horas(p)
                }
                for p in propostas
            ]
        }

    def _prazo_expirou(self, solicitacao: SolicitacaoCotacao) -> bool:
        """Verifica se o prazo limite da proposta expirou"""
        if not solicitacao.data_limite_proposta:
            return False
        return datetime.now() > solicitacao.data_limite_proposta

    def _calcular_tempo_resposta_horas(self, proposta: PropostaFornecedor) -> Optional[float]:
        """
        Calcula o tempo de resposta em horas.

        Tempo = data_recebimento - data_envio_solicitacao
        """
        if not proposta.data_envio_solicitacao:
            return None
        if not proposta.data_recebimento:
            return None

        diferenca = proposta.data_recebimento - proposta.data_envio_solicitacao
        horas = diferenca.total_seconds() / 3600
        return round(horas, 2)

    def registrar_resposta_proposta(
        self,
        db: Session,
        proposta_id: int,
        data_recebimento: Optional[datetime] = None
    ) -> dict:
        """
        Registra o recebimento de uma proposta e atualiza estatisticas do fornecedor.

        Args:
            db: Sessao do banco
            proposta_id: ID da proposta
            data_recebimento: Data/hora do recebimento (padrao: agora)

        Returns:
            Dict com resultado da operacao
        """
        proposta = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.id == proposta_id
        ).first()

        if not proposta:
            return {"error": "Proposta nao encontrada"}

        if proposta.status != StatusProposta.PENDENTE:
            return {"error": "Proposta ja foi respondida anteriormente"}

        # Atualizar proposta
        proposta.data_recebimento = data_recebimento or datetime.now()
        proposta.status = StatusProposta.RECEBIDA

        # Calcular tempo de resposta
        tempo_resposta = self._calcular_tempo_resposta_horas(proposta)

        # Atualizar estatisticas do fornecedor
        self._atualizar_estatisticas_fornecedor(
            db,
            proposta.fornecedor_id,
            tempo_resposta
        )

        # Verificar se deve atualizar status da solicitacao
        self._verificar_atualizar_status_solicitacao(db, proposta.solicitacao_id)

        db.commit()

        return {
            "sucesso": True,
            "proposta_id": proposta_id,
            "fornecedor_id": proposta.fornecedor_id,
            "tempo_resposta_horas": tempo_resposta,
            "status": proposta.status.value
        }

    def _atualizar_estatisticas_fornecedor(
        self,
        db: Session,
        fornecedor_id: int,
        tempo_resposta_horas: Optional[float]
    ):
        """
        Atualiza as estatisticas de tempo de resposta do fornecedor.

        Usa media movel ponderada para dar mais peso a respostas recentes.
        """
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == fornecedor_id
        ).first()

        if not fornecedor:
            return

        # Buscar todas as propostas respondidas deste fornecedor
        propostas_respondidas = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.fornecedor_id == fornecedor_id,
            PropostaFornecedor.data_recebimento.isnot(None),
            PropostaFornecedor.data_envio_solicitacao.isnot(None)
        ).all()

        if not propostas_respondidas:
            return

        # Calcular tempo medio de resposta
        tempos = []
        for p in propostas_respondidas:
            tempo = self._calcular_tempo_resposta_horas(p)
            if tempo is not None and tempo > 0:
                tempos.append(tempo)

        if tempos:
            tempo_medio_horas = sum(tempos) / len(tempos)

            # Atualizar o rating baseado no tempo de resposta
            # Escala: < 4h = 5.0, 4-12h = 4.0, 12-24h = 3.0, 24-48h = 2.0, > 48h = 1.0
            rating_tempo = self._calcular_rating_tempo_resposta(tempo_medio_horas)

            # Combinar com rating existente (se houver)
            # Peso: 60% preco/qualidade (rating atual), 40% tempo de resposta
            if fornecedor.rating and fornecedor.rating > 0:
                novo_rating = (float(fornecedor.rating) * 0.6) + (rating_tempo * 0.4)
            else:
                novo_rating = rating_tempo

            fornecedor.rating = Decimal(str(round(novo_rating, 2)))

    def _calcular_rating_tempo_resposta(self, tempo_horas: float) -> float:
        """
        Calcula rating (0-5) baseado no tempo de resposta em horas.

        Escala:
        - < 4 horas: 5.0 (excelente)
        - 4-12 horas: 4.0 (muito bom)
        - 12-24 horas: 3.0 (bom)
        - 24-48 horas: 2.0 (regular)
        - > 48 horas: 1.0 (ruim)
        """
        if tempo_horas < 4:
            return 5.0
        elif tempo_horas < 12:
            return 4.0
        elif tempo_horas < 24:
            return 3.0
        elif tempo_horas < 48:
            return 2.0
        else:
            return 1.0

    def _verificar_atualizar_status_solicitacao(
        self,
        db: Session,
        solicitacao_id: int
    ):
        """
        Verifica se a solicitacao deve mudar de status.

        ENVIADA -> EM_COTACAO: quando recebe primeira resposta
        """
        solicitacao = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.id == solicitacao_id
        ).first()

        if not solicitacao:
            return

        # Se ainda esta ENVIADA e recebeu resposta, mudar para EM_COTACAO
        if solicitacao.status == StatusSolicitacao.ENVIADA:
            propostas_recebidas = db.query(PropostaFornecedor).filter(
                PropostaFornecedor.solicitacao_id == solicitacao_id,
                PropostaFornecedor.status != StatusProposta.PENDENTE
            ).count()

            if propostas_recebidas > 0:
                solicitacao.status = StatusSolicitacao.EM_COTACAO

    def obter_ranking_fornecedores(
        self,
        db: Session,
        tenant_id: int,
        limite: int = 10
    ) -> List[dict]:
        """
        Obtem ranking dos melhores fornecedores por tempo de resposta.

        Args:
            db: Sessao do banco
            tenant_id: ID do tenant
            limite: Quantidade de fornecedores a retornar

        Returns:
            Lista de fornecedores ordenados por rating
        """
        fornecedores = db.query(Fornecedor).filter(
            Fornecedor.tenant_id == tenant_id,
            Fornecedor.ativo == True
        ).order_by(desc(Fornecedor.rating)).limit(limite).all()

        resultado = []
        for f in fornecedores:
            # Buscar estatisticas de propostas
            total_propostas = db.query(PropostaFornecedor).filter(
                PropostaFornecedor.fornecedor_id == f.id
            ).count()

            propostas_respondidas = db.query(PropostaFornecedor).filter(
                PropostaFornecedor.fornecedor_id == f.id,
                PropostaFornecedor.status != StatusProposta.PENDENTE
            ).count()

            # Calcular tempo medio de resposta
            propostas_com_tempo = db.query(PropostaFornecedor).filter(
                PropostaFornecedor.fornecedor_id == f.id,
                PropostaFornecedor.data_recebimento.isnot(None),
                PropostaFornecedor.data_envio_solicitacao.isnot(None)
            ).all()

            tempos = [
                self._calcular_tempo_resposta_horas(p)
                for p in propostas_com_tempo
            ]
            tempos = [t for t in tempos if t is not None]
            tempo_medio = round(sum(tempos) / len(tempos), 2) if tempos else None

            taxa_resposta = round(
                propostas_respondidas / total_propostas * 100, 1
            ) if total_propostas > 0 else 0

            resultado.append({
                "fornecedor_id": f.id,
                "razao_social": f.razao_social,
                "nome_fantasia": f.nome_fantasia,
                "rating": float(f.rating) if f.rating else 0,
                "total_cotacoes_solicitadas": total_propostas,
                "total_cotacoes_respondidas": propostas_respondidas,
                "taxa_resposta_percentual": taxa_resposta,
                "tempo_medio_resposta_horas": tempo_medio,
                "classificacao_tempo": self._classificar_tempo(tempo_medio) if tempo_medio else "Sem dados"
            })

        return resultado

    def _classificar_tempo(self, tempo_horas: float) -> str:
        """Retorna classificacao textual do tempo de resposta"""
        if tempo_horas < 4:
            return "Excelente"
        elif tempo_horas < 12:
            return "Muito bom"
        elif tempo_horas < 24:
            return "Bom"
        elif tempo_horas < 48:
            return "Regular"
        else:
            return "Lento"

    def obter_estatisticas_fornecedor(
        self,
        db: Session,
        fornecedor_id: int
    ) -> dict:
        """
        Obtem estatisticas detalhadas de um fornecedor especifico.

        Args:
            db: Sessao do banco
            fornecedor_id: ID do fornecedor

        Returns:
            Dict com estatisticas completas
        """
        fornecedor = db.query(Fornecedor).filter(
            Fornecedor.id == fornecedor_id
        ).first()

        if not fornecedor:
            return {"error": "Fornecedor nao encontrado"}

        # Buscar todas as propostas
        propostas = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.fornecedor_id == fornecedor_id
        ).all()

        # Contar por status
        por_status = {}
        for p in propostas:
            status = p.status.value
            if status not in por_status:
                por_status[status] = 0
            por_status[status] += 1

        # Calcular tempos de resposta
        tempos = []
        for p in propostas:
            tempo = self._calcular_tempo_resposta_horas(p)
            if tempo is not None:
                tempos.append(tempo)

        tempo_medio = round(sum(tempos) / len(tempos), 2) if tempos else None
        tempo_minimo = round(min(tempos), 2) if tempos else None
        tempo_maximo = round(max(tempos), 2) if tempos else None

        # Contar vitorias (propostas aprovadas/vencedoras)
        vitorias = sum(
            1 for p in propostas
            if p.status in [StatusProposta.APROVADA, StatusProposta.VENCEDORA]
        )

        taxa_sucesso = round(
            vitorias / len(propostas) * 100, 1
        ) if propostas else 0

        return {
            "fornecedor_id": fornecedor_id,
            "razao_social": fornecedor.razao_social,
            "nome_fantasia": fornecedor.nome_fantasia,
            "rating": float(fornecedor.rating) if fornecedor.rating else 0,
            "estatisticas": {
                "total_cotacoes": len(propostas),
                "por_status": por_status,
                "vitorias": vitorias,
                "taxa_sucesso_percentual": taxa_sucesso
            },
            "tempo_resposta": {
                "media_horas": tempo_medio,
                "minimo_horas": tempo_minimo,
                "maximo_horas": tempo_maximo,
                "classificacao": self._classificar_tempo(tempo_medio) if tempo_medio else "Sem dados"
            },
            "historico_compras": {
                "total_compras": fornecedor.total_compras,
                "valor_total": float(fornecedor.valor_total_comprado) if fornecedor.valor_total_comprado else 0
            }
        }


# Instancia global
fornecedor_ranking_service = FornecedorRankingService()
