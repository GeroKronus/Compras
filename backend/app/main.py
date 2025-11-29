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
    return {"version": "1.0050", "status": "ok"}

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
