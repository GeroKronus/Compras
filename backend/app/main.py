from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.middleware.tenant_middleware import TenantMiddleware
from app.api.routes import auth, tenants, categorias, produtos, fornecedores, cotacoes, pedidos, emails, ia_usage, dashboard, auditoria, usuarios, setup
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de Tenant (será aplicado após autenticação)
app.add_middleware(TenantMiddleware)

# Diretório do frontend estático
# Em produção (Docker): /app/static
# Em desenvolvimento: backend/static (não existe)
STATIC_DIR = "/app/static" if os.path.exists("/app/static") else os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Rota de health check
@app.get("/health")
def health_check():
    """Health check para monitoramento"""
    return {"status": "healthy"}


# Endpoint de versão simples (sem dependências)
@app.get("/api/v1/version")
def get_api_version():
    """Retorna versão do backend para verificar deploy"""
    return {"version": "1.0067", "status": "ok"}

# Debug: testar pypdf
@app.get("/debug/pypdf")
def debug_pypdf():
    """Testa se pypdf está instalado e funcionando."""
    resultado = {"etapas": []}
    try:
        resultado["etapas"].append("iniciando...")
        from pypdf import PdfReader
        resultado["etapas"].append("import pypdf OK")
        resultado["pypdf_ok"] = True
        resultado["versao"] = str(PdfReader)
    except ImportError as e:
        resultado["pypdf_ok"] = False
        resultado["erro_import"] = str(e)
    except Exception as e:
        import traceback
        resultado["pypdf_ok"] = False
        resultado["erro"] = str(e)
        resultado["traceback"] = traceback.format_exc()
    return resultado


# Debug: reprocessar email específico
@app.post("/debug/reprocessar/{email_id}")
def reprocessar_email(email_id: int):
    """Reprocessa um email específico com extração de PDF."""
    import traceback
    from datetime import datetime
    resultado = {"email_id": email_id, "etapas": []}

    try:
        from app.database import SessionLocal
        from app.models.email_processado import EmailProcessado
        resultado["etapas"].append("imports db ok")

        db = SessionLocal()
        resultado["etapas"].append("db session ok")

        email_proc = db.query(EmailProcessado).filter(
            EmailProcessado.id == email_id
        ).first()

        if not email_proc:
            db.close()
            resultado["erro"] = "Email não encontrado no banco"
            return resultado

        resultado["email_uid"] = email_proc.email_uid
        resultado["remetente"] = email_proc.remetente
        resultado["assunto"] = email_proc.assunto
        resultado["etapas"].append("email encontrado no banco")

        # Buscar email via IMAP
        import imaplib
        import email as email_lib
        from app.config import settings

        mail = imaplib.IMAP4_SSL(
            settings.IMAP_HOST or 'imappro.zoho.com',
            settings.IMAP_PORT or 993
        )
        mail.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        mail.select('INBOX')
        resultado["etapas"].append("conectado IMAP")

        fetch_result, msg_data = mail.fetch(email_proc.email_uid.encode(), '(RFC822)')
        resultado["etapas"].append(f"fetch: {fetch_result}")

        if fetch_result != 'OK' or not msg_data or not msg_data[0]:
            mail.logout()
            resultado["erro"] = "Email não encontrado no IMAP"
            db.close()
            return resultado

        raw_email = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw_email)
        resultado["etapas"].append("email parseado")

        # Extrair corpo
        from app.services.email_classifier import email_classifier
        resultado["etapas"].append("classifier importado")

        corpo = email_classifier._extrair_corpo(msg)
        resultado["corpo_tamanho"] = len(corpo) if corpo else 0
        resultado["etapas"].append("corpo extraido")

        # Extrair PDF
        try:
            conteudo_pdf = email_classifier._extrair_anexos_pdf(msg)
            resultado["pdf_tamanho"] = len(conteudo_pdf) if conteudo_pdf else 0
            resultado["pdf_preview"] = conteudo_pdf[:500] if conteudo_pdf else "(nenhum)"
            resultado["etapas"].append("PDF extraido")
        except Exception as pdf_err:
            resultado["pdf_erro"] = str(pdf_err)
            resultado["etapas"].append(f"erro PDF: {pdf_err}")
            conteudo_pdf = None

        mail.logout()

        # Extrair dados via IA
        try:
            from app.services.ai_service import ai_service
            import re
            import json

            dados_extraidos = ai_service.extrair_dados_proposta_email(corpo, conteudo_pdf)
            resultado["dados_extraidos"] = dados_extraidos
            resultado["etapas"].append("IA extraiu dados")

            # Atualizar registro do email
            email_proc.tipo = "resposta_cotacao"
            email_proc.dados_extraidos = json.dumps(dados_extraidos)
            email_proc.status = "processado"
            email_proc.data_processamento = datetime.utcnow()
            resultado["etapas"].append("email atualizado")

            # Tentar encontrar solicitação pelo assunto (SC-XXXX-XXXXX)
            from app.models.cotacao import SolicitacaoCotacao, PropostaFornecedor, ItemSolicitacao, ItemProposta
            from app.models.fornecedor import Fornecedor

            match = re.search(r'SC-\d{4}-\d{5}', email_proc.assunto or "")
            if match:
                numero_solicitacao = match.group()
                solicitacao = db.query(SolicitacaoCotacao).filter(
                    SolicitacaoCotacao.numero == numero_solicitacao,
                    SolicitacaoCotacao.tenant_id == email_proc.tenant_id
                ).first()

                if solicitacao:
                    email_proc.solicitacao_id = solicitacao.id
                    resultado["solicitacao_id"] = solicitacao.id
                    resultado["etapas"].append(f"solicitacao encontrada: {numero_solicitacao}")

                    # Buscar fornecedor pelo email remetente
                    fornecedor = db.query(Fornecedor).filter(
                        Fornecedor.email_principal == email_proc.remetente,
                        Fornecedor.tenant_id == email_proc.tenant_id
                    ).first()

                    if fornecedor:
                        email_proc.fornecedor_id = fornecedor.id
                        resultado["fornecedor_id"] = fornecedor.id
                        resultado["etapas"].append(f"fornecedor: {fornecedor.razao_social}")

                        # Buscar ou criar proposta
                        proposta = db.query(PropostaFornecedor).filter(
                            PropostaFornecedor.solicitacao_id == solicitacao.id,
                            PropostaFornecedor.fornecedor_id == fornecedor.id,
                            PropostaFornecedor.tenant_id == email_proc.tenant_id
                        ).first()

                        if not proposta:
                            proposta = PropostaFornecedor(
                                solicitacao_id=solicitacao.id,
                                fornecedor_id=fornecedor.id,
                                tenant_id=email_proc.tenant_id,
                                status="RECEBIDA"
                            )
                            db.add(proposta)
                            db.flush()
                            resultado["etapas"].append("proposta criada")
                        else:
                            resultado["etapas"].append("proposta existente")

                        # Atualizar dados da proposta
                        if dados_extraidos.get('prazo_entrega_dias'):
                            proposta.prazo_entrega = dados_extraidos['prazo_entrega_dias']
                        if dados_extraidos.get('condicoes_pagamento'):
                            proposta.condicoes_pagamento = dados_extraidos['condicoes_pagamento']
                        proposta.status = "RECEBIDA"

                        # Vincular email à proposta
                        email_proc.proposta_id = proposta.id

                        # Criar/atualizar itens da proposta
                        itens_extraidos = dados_extraidos.get('itens', [])
                        itens_solicitacao = db.query(ItemSolicitacao).filter(
                            ItemSolicitacao.solicitacao_id == solicitacao.id
                        ).order_by(ItemSolicitacao.id).all()

                        valor_total = 0
                        for idx, item_sol in enumerate(itens_solicitacao):
                            # Buscar preço correspondente
                            preco = None
                            for item_ext in itens_extraidos:
                                if item_ext.get('indice') == idx or item_ext.get('indice') == idx + 1:
                                    preco = item_ext.get('preco_unitario')
                                    break
                            if preco is None and idx < len(itens_extraidos):
                                preco = itens_extraidos[idx].get('preco_unitario')

                            if preco:
                                # Buscar ou criar item_proposta
                                item_proposta = db.query(ItemProposta).filter(
                                    ItemProposta.proposta_id == proposta.id,
                                    ItemProposta.item_solicitacao_id == item_sol.id
                                ).first()

                                if not item_proposta:
                                    item_proposta = ItemProposta(
                                        proposta_id=proposta.id,
                                        item_solicitacao_id=item_sol.id,
                                        tenant_id=email_proc.tenant_id
                                    )
                                    db.add(item_proposta)

                                item_proposta.preco_unitario = preco
                                valor_total += preco * item_sol.quantidade

                        proposta.valor_total = valor_total
                        resultado["valor_total"] = valor_total
                        resultado["etapas"].append(f"itens atualizados, valor_total={valor_total}")
                    else:
                        resultado["etapas"].append("fornecedor NAO encontrado")
                else:
                    resultado["etapas"].append(f"solicitacao {numero_solicitacao} NAO encontrada")
            else:
                resultado["etapas"].append("numero SC nao encontrado no assunto")

            db.commit()
            resultado["sucesso"] = True
            resultado["etapas"].append("salvo no banco")

        except Exception as ia_err:
            resultado["ia_erro"] = str(ia_err)
            resultado["ia_traceback"] = traceback.format_exc()
            resultado["etapas"].append(f"erro IA: {ia_err}")
            db.rollback()

        db.close()

    except Exception as e:
        resultado["erro"] = str(e)
        resultado["traceback"] = traceback.format_exc()

    return resultado

# Gabarito de valores esperados dos PDFs
GABARITO = {
    "kronus": {
        "fornecedor": "Kronus",
        "itens": [
            {"produto": "Avental de Raspa", "qtd": 4, "preco_unitario": 5.00, "total": 20.00},
            {"produto": "Disco Diamantado 110mm", "qtd": 5, "preco_unitario": 5.00, "total": 25.00}
        ],
        "valor_total": 45.00,
        "prazo_entrega_dias": 10,
        "condicoes_pagamento": "a vista"
    },
    "picstone": {
        "fornecedor": "Picstone",
        "itens": [
            {"produto": "Avental de Raspa", "qtd": 4, "preco_unitario": 6.00, "total": 24.00},
            {"produto": "Disco Diamantado 110mm", "qtd": 5, "preco_unitario": 5.00, "total": 25.00}
        ],
        "valor_total": 49.00,
        "prazo_entrega_dias": 15,
        "condicoes_pagamento": "30 dias"
    }
}

@app.get("/debug/gabarito")
def get_gabarito():
    """Retorna valores esperados (gabarito) dos PDFs de teste."""
    return GABARITO


@app.post("/debug/limpar-propostas/{solicitacao_id}")
def limpar_propostas(solicitacao_id: int):
    """Limpa todas as propostas de uma solicitação (mantém a solicitação e emails)."""
    import traceback
    resultado = {"solicitacao_id": solicitacao_id, "etapas": []}

    try:
        from app.database import SessionLocal
        from app.models.cotacao import SolicitacaoCotacao, PropostaFornecedor, ItemProposta
        from app.models.email_processado import EmailProcessado

        db = SessionLocal()

        # Verificar solicitação
        solicitacao = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.id == solicitacao_id
        ).first()

        if not solicitacao:
            db.close()
            resultado["erro"] = "Solicitação não encontrada"
            return resultado

        resultado["numero"] = solicitacao.numero
        resultado["etapas"].append(f"solicitação encontrada: {solicitacao.numero}")

        # Buscar propostas
        propostas = db.query(PropostaFornecedor).filter(
            PropostaFornecedor.solicitacao_id == solicitacao_id
        ).all()

        resultado["propostas_encontradas"] = len(propostas)

        # Deletar itens das propostas
        itens_deletados = 0
        for proposta in propostas:
            itens = db.query(ItemProposta).filter(
                ItemProposta.proposta_id == proposta.id
            ).all()
            for item in itens:
                db.delete(item)
                itens_deletados += 1

        resultado["itens_deletados"] = itens_deletados
        resultado["etapas"].append(f"itens deletados: {itens_deletados}")

        # Deletar propostas
        for proposta in propostas:
            db.delete(proposta)

        resultado["propostas_deletadas"] = len(propostas)
        resultado["etapas"].append(f"propostas deletadas: {len(propostas)}")

        # Resetar emails processados (marcar como pendente novamente)
        emails = db.query(EmailProcessado).filter(
            EmailProcessado.solicitacao_id == solicitacao_id
        ).all()

        for email_proc in emails:
            email_proc.status = "pendente"
            email_proc.proposta_id = None
            email_proc.dados_extraidos = None
            email_proc.data_processamento = None

        resultado["emails_resetados"] = len(emails)
        resultado["etapas"].append(f"emails resetados: {len(emails)}")

        db.commit()
        db.close()

        resultado["sucesso"] = True
        resultado["etapas"].append("banco limpo com sucesso")

    except Exception as e:
        resultado["erro"] = str(e)
        resultado["traceback"] = traceback.format_exc()

    return resultado


@app.post("/debug/teste-extracao/{solicitacao_id}")
def teste_extracao(solicitacao_id: int):
    """
    Executa ciclo completo de teste:
    1. Limpa propostas da solicitação
    2. Reprocessa emails com PDF
    3. Compara resultados com gabarito
    """
    import traceback
    resultado = {
        "solicitacao_id": solicitacao_id,
        "ciclo": [],
        "resultados": {},
        "comparacao": [],
        "confiabilidade": {}
    }

    try:
        # Passo 1: Limpar propostas
        resultado["ciclo"].append("limpando propostas...")
        limpeza = limpar_propostas(solicitacao_id)
        resultado["limpeza"] = limpeza

        if not limpeza.get("sucesso"):
            resultado["erro"] = "Falha na limpeza"
            return resultado

        resultado["ciclo"].append(f"limpeza OK - {limpeza.get('propostas_deletadas', 0)} propostas removidas")

        # Passo 2: Buscar emails para reprocessar
        from app.database import SessionLocal
        from app.models.email_processado import EmailProcessado
        from app.models.cotacao import SolicitacaoCotacao

        db = SessionLocal()

        solicitacao = db.query(SolicitacaoCotacao).filter(
            SolicitacaoCotacao.id == solicitacao_id
        ).first()

        if not solicitacao:
            db.close()
            resultado["erro"] = "Solicitação não encontrada"
            return resultado

        # Buscar emails com o número da solicitação no assunto
        import re
        emails_proc = db.query(EmailProcessado).filter(
            EmailProcessado.assunto.like(f"%{solicitacao.numero}%"),
            EmailProcessado.tenant_id == solicitacao.tenant_id
        ).all()

        resultado["ciclo"].append(f"encontrados {len(emails_proc)} emails para processar")
        db.close()

        # Passo 3: Reprocessar cada email
        for email_proc in emails_proc:
            resultado["ciclo"].append(f"processando email {email_proc.id} ({email_proc.remetente})...")
            reprocessamento = reprocessar_email(email_proc.id)

            # Identificar fornecedor pelo remetente
            remetente = email_proc.remetente.lower()
            fornecedor_key = None
            if "kronus" in remetente or "isidorio" in remetente:
                fornecedor_key = "kronus"
            elif "picstone" in remetente:
                fornecedor_key = "picstone"

            resultado["resultados"][fornecedor_key or email_proc.remetente] = {
                "email_id": email_proc.id,
                "remetente": email_proc.remetente,
                "dados_extraidos": reprocessamento.get("dados_extraidos"),
                "valor_total_calculado": reprocessamento.get("valor_total"),
                "sucesso": reprocessamento.get("sucesso", False),
                "etapas": reprocessamento.get("etapas", [])
            }

            resultado["ciclo"].append(f"email {email_proc.id} processado - sucesso: {reprocessamento.get('sucesso')}")

        # Passo 4: Comparar com gabarito
        for fornecedor_key, esperado in GABARITO.items():
            if fornecedor_key in resultado["resultados"]:
                extraido = resultado["resultados"][fornecedor_key]
                dados = extraido.get("dados_extraidos", {})

                comp = {
                    "fornecedor": fornecedor_key,
                    "itens_corretos": True,
                    "detalhes": []
                }

                # Comparar itens
                itens_ext = dados.get("itens", [])
                for idx, item_esp in enumerate(esperado["itens"]):
                    if idx < len(itens_ext):
                        preco_ext = itens_ext[idx].get("preco_unitario", 0)
                        preco_esp = item_esp["preco_unitario"]
                        diff = abs(preco_ext - preco_esp)
                        correto = diff < 0.01

                        comp["detalhes"].append({
                            "item": item_esp["produto"],
                            "esperado": preco_esp,
                            "extraido": preco_ext,
                            "correto": correto,
                            "diferenca": diff
                        })

                        if not correto:
                            comp["itens_corretos"] = False
                    else:
                        comp["detalhes"].append({
                            "item": item_esp["produto"],
                            "esperado": item_esp["preco_unitario"],
                            "extraido": None,
                            "correto": False,
                            "erro": "item não extraído"
                        })
                        comp["itens_corretos"] = False

                # Comparar valor total
                valor_ext = extraido.get("valor_total_calculado", 0)
                valor_esp = esperado["valor_total"]
                diff_total = abs(valor_ext - valor_esp) if valor_ext else valor_esp

                comp["valor_total_esperado"] = valor_esp
                comp["valor_total_extraido"] = valor_ext
                comp["valor_total_correto"] = diff_total < 0.01

                resultado["comparacao"].append(comp)

        # Calcular confiabilidade
        total_itens = 0
        itens_corretos = 0
        for comp in resultado["comparacao"]:
            for det in comp["detalhes"]:
                total_itens += 1
                if det.get("correto"):
                    itens_corretos += 1

        resultado["confiabilidade"] = {
            "itens_testados": total_itens,
            "itens_corretos": itens_corretos,
            "taxa_acerto": round(itens_corretos / total_itens * 100, 2) if total_itens > 0 else 0,
            "todos_corretos": itens_corretos == total_itens
        }

        resultado["sucesso"] = True

    except Exception as e:
        resultado["erro"] = str(e)
        resultado["traceback"] = traceback.format_exc()

    return resultado


# Debug: verificar caminho do frontend
@app.get("/debug/static")
def debug_static():
    """Debug: verificar se frontend existe"""
    try:
        index_path = os.path.join(STATIC_DIR, "index.html")
        files = []
        if os.path.exists(STATIC_DIR):
            files = os.listdir(STATIC_DIR)
        return {
            "static_dir": STATIC_DIR,
            "index_path": index_path,
            "static_exists": os.path.exists(STATIC_DIR),
            "index_exists": os.path.exists(index_path),
            "cwd": os.getcwd(),
            "files_in_static": files
        }
    except Exception as e:
        return {"error": str(e)}

# Rota raiz - serve frontend se existir, senão retorna info da API
@app.get("/")
def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Sistema de Compras Multi-Tenant API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# Incluir routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(tenants.router, prefix=f"{settings.API_V1_STR}/tenants", tags=["tenants"])
app.include_router(categorias.router, prefix=f"{settings.API_V1_STR}/categorias", tags=["categorias"])
app.include_router(produtos.router, prefix=f"{settings.API_V1_STR}/produtos", tags=["produtos"])
app.include_router(fornecedores.router, prefix=f"{settings.API_V1_STR}/fornecedores", tags=["fornecedores"])
app.include_router(cotacoes.router, prefix=f"{settings.API_V1_STR}/cotacoes", tags=["cotacoes"])
app.include_router(pedidos.router, prefix=f"{settings.API_V1_STR}/pedidos", tags=["pedidos"])
app.include_router(emails.router, prefix=f"{settings.API_V1_STR}/emails", tags=["emails"])
app.include_router(ia_usage.router, prefix=f"{settings.API_V1_STR}/ia", tags=["ia"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(auditoria.router, prefix=f"{settings.API_V1_STR}/auditoria", tags=["auditoria"])
app.include_router(usuarios.router, prefix=f"{settings.API_V1_STR}/usuarios", tags=["usuarios"])
app.include_router(setup.router, prefix=f"{settings.API_V1_STR}/setup", tags=["setup"])


# Evento de startup (jobs agendados)
@app.on_event("startup")
def startup_event():
    print(f"[STARTUP] {settings.PROJECT_NAME} iniciado!")
    print(f"[STARTUP] Documentacao: http://localhost:8000/docs")
    print(f"[STARTUP] Ambiente: {settings.ENVIRONMENT}")

    # Criar tabelas do banco de dados automaticamente
    try:
        from app.database import engine, SessionLocal
        from app.models.base import Base
        # Importar todos os models para registrar no metadata
        from app.models import (
            tenant, usuario, categoria, produto, fornecedor,
            cotacao, pedido, auditoria_escolha, uso_ia,
            email_processado, produto_fornecedor
        )
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] Tabelas do banco de dados criadas/verificadas!")

        # Corrigir tenant_ids das propostas automaticamente
        from sqlalchemy import text
        db = SessionLocal()
        try:
            # Sincronizar tenant_id das propostas com a solicitacao
            result = db.execute(text("""
                UPDATE propostas_fornecedor p
                SET tenant_id = s.tenant_id
                FROM solicitacoes_cotacao s
                WHERE p.solicitacao_id = s.id
                AND p.tenant_id != s.tenant_id
            """))
            if result.rowcount > 0:
                print(f"[STARTUP] Corrigidos {result.rowcount} propostas com tenant_id incorreto")
            db.commit()
        except Exception as e2:
            db.rollback()
            print(f"[STARTUP] Erro ao corrigir tenant_ids: {e2}")
        finally:
            db.close()

    except Exception as e:
        print(f"[STARTUP] Erro ao criar tabelas: {e}")

    # Iniciar job de verificacao de emails automaticamente
    # Pode ser desabilitado com ENABLE_SCHEDULED_JOBS=false
    enable_jobs = getattr(settings, 'ENABLE_SCHEDULED_JOBS', True)
    # Converter para bool corretamente (variaveis de ambiente sao strings)
    if isinstance(enable_jobs, str):
        enable_jobs = enable_jobs.lower() not in ('false', '0', 'no', '')
    if enable_jobs:
        try:
            from app.jobs.email_job import iniciar_scheduler
            intervalo = int(getattr(settings, 'EMAIL_CHECK_INTERVAL', 5))
            iniciar_scheduler(intervalo_minutos=intervalo)
            print(f"[STARTUP] Job de verificacao de emails iniciado (a cada {intervalo} min)")
        except Exception as e:
            print(f"[STARTUP] Erro ao iniciar job de emails: {e}")


@app.on_event("shutdown")
def shutdown_event():
    # Parar scheduler se estiver rodando
    try:
        from app.jobs.email_job import parar_scheduler
        parar_scheduler()
    except:
        pass
    print("[SHUTDOWN] Sistema encerrado!")


# Catch-all para SPA - qualquer rota não-API retorna index.html ou arquivos estáticos
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Se for rota de API ou interna, deixa passar
    if full_path.startswith("api/") or full_path.startswith("debug/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
        return {"detail": "Not Found"}

    # Tentar servir arquivo estático (assets, vite.svg, etc)
    static_file = os.path.join(STATIC_DIR, full_path)
    if os.path.isfile(static_file):
        return FileResponse(static_file)

    # Retorna o index.html para o React Router tratar
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}
