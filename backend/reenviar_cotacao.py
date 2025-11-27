"""
Script para reenviar emails de cotacao com o novo template
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import SolicitacaoCotacao, PropostaFornecedor, Fornecedor, ItemSolicitacao, Produto
from app.services.email_service import email_service

def reenviar_cotacao(solicitacao_id: int = 1, tenant_id: int = 4):
    """Reenvia emails de cotacao para fornecedores"""
    db = SessionLocal()

    try:
        # Buscar solicitacao
        solicitacao = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.id == solicitacao_id,
            SolicitacaoCotacao.tenant_id == tenant_id
        ).first()

        if not solicitacao:
            print(f"Solicitacao {solicitacao_id} nao encontrada!")
            return

        print(f"Solicitacao encontrada: {solicitacao.numero} - {solicitacao.titulo}")

        # Buscar itens da solicitacao
        itens_db = db.query(ItemSolicitacao).filter(
            ItemSolicitacao.solicitacao_id == solicitacao_id
        ).all()

        itens_email = []
        for item in itens_db:
            produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
            itens_email.append({
                'produto_nome': produto.nome if produto else 'N/A',
                'quantidade': item.quantidade,
                'unidade_medida': item.unidade_medida or (produto.unidade_medida if produto else 'UN'),
                'especificacoes': item.especificacoes or ''
            })

        print(f"Itens: {len(itens_email)}")
        for i, item in enumerate(itens_email, 1):
            print(f"  {i}. {item['produto_nome']} - {item['quantidade']} {item['unidade_medida']}")

        # Buscar propostas/fornecedores
        propostas = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id,
            PropostaFornecedor.tenant_id == tenant_id
        ).all()

        print(f"\nPropostas encontradas: {len(propostas)}")

        data_limite_str = None
        if solicitacao.data_limite_proposta:
            data_limite_str = solicitacao.data_limite_proposta.strftime('%d/%m/%Y')

        emails_enviados = []
        emails_falha = []

        for proposta in propostas:
            fornecedor = db.query(Fornecedor).filter(Fornecedor.id == proposta.fornecedor_id).first()
            if not fornecedor:
                print(f"  Fornecedor {proposta.fornecedor_id} nao encontrado")
                continue

            nome = fornecedor.razao_social or fornecedor.nome_fantasia or "Fornecedor"
            email = fornecedor.email_principal

            print(f"\nEnviando para: {nome} ({email})")

            if not email:
                print(f"  -> SEM EMAIL CADASTRADO!")
                emails_falha.append(f"{nome} (sem email)")
                continue

            if not email_service.is_configured:
                print(f"  -> SERVICO DE EMAIL NAO CONFIGURADO!")
                emails_falha.append(f"{nome} (servico nao configurado)")
                continue

            # Enviar email com novo template
            sucesso = email_service.enviar_solicitacao_cotacao_multiplos_itens(
                fornecedor_email=email,
                fornecedor_nome=nome,
                solicitacao_numero=solicitacao.numero,
                solicitacao_titulo=solicitacao.titulo,
                itens=itens_email,
                observacoes=solicitacao.observacoes,
                solicitacao_id=solicitacao.id,
                data_limite=data_limite_str
            )

            if sucesso:
                print(f"  -> ENVIADO COM SUCESSO!")
                emails_enviados.append(nome)
            else:
                print(f"  -> FALHA NO ENVIO!")
                emails_falha.append(nome)

        print(f"\n=== RESUMO ===")
        print(f"Emails enviados: {len(emails_enviados)}")
        for nome in emails_enviados:
            print(f"  - {nome}")
        print(f"Falhas: {len(emails_falha)}")
        for nome in emails_falha:
            print(f"  - {nome}")

    finally:
        db.close()

if __name__ == "__main__":
    # Reenviar para a solicitacao SC-2025-00001 (id=1)
    reenviar_cotacao(solicitacao_id=1, tenant_id=4)
