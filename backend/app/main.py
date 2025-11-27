from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware.tenant_middleware import TenantMiddleware
from app.api.routes import auth, tenants, categorias, produtos, fornecedores, cotacoes, pedidos, emails, ia_usage, dashboard, auditoria, usuarios

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

# Rota de health check
@app.get("/")
def root():
    return {
        "message": "Sistema de Compras Multi-Tenant API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
def health_check():
    """Health check para monitoramento"""
    return {"status": "healthy"}


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
