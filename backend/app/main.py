from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.middleware.tenant_middleware import TenantMiddleware
from app.api.routes import auth, tenants, categorias, produtos, fornecedores, cotacoes, pedidos, emails, ia_usage, dashboard, auditoria, usuarios
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
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Rota de health check
@app.get("/health")
def health_check():
    """Health check para monitoramento"""
    return {"status": "healthy"}

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


# Evento de startup (jobs agendados)
@app.on_event("startup")
def startup_event():
    print(f"[STARTUP] {settings.PROJECT_NAME} iniciado!")
    print(f"[STARTUP] Documentacao: http://localhost:8000/docs")
    print(f"[STARTUP] Ambiente: {settings.ENVIRONMENT}")

    # Iniciar job de verificacao de emails se habilitado
    if getattr(settings, 'ENABLE_SCHEDULED_JOBS', False):
        try:
            from app.jobs.email_job import iniciar_scheduler
            iniciar_scheduler(intervalo_minutos=5)
            print("[STARTUP] Job de verificacao de emails iniciado")
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


# Servir frontend estático (em produção)
# Monta assets se existir
assets_dir = os.path.join(STATIC_DIR, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Catch-all para SPA - qualquer rota não-API retorna index.html
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Se for rota de API ou interna, deixa passar
    if full_path.startswith("api/") or full_path.startswith("debug/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
        return {"detail": "Not Found"}

    # Retorna o index.html para o React Router tratar
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}
