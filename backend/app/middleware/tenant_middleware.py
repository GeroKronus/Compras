from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_access_token
from app.core.tenant_context import set_current_tenant_id, clear_current_tenant_id
from jose import JWTError


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware que identifica o tenant em TODAS as requisições autenticadas
    e configura o contexto para isolamento de dados

    Fluxo:
    1. Extrai o token JWT do header Authorization
    2. Decodifica o token e obtém tenant_id e user_id
    3. Adiciona ao contexto da request (request.state)
    4. Configura tenant_id no ContextVar para acesso global

    IMPORTANTE: Este middleware garante que TODAS as requisições
    autenticadas tenham um tenant_id associado, impedindo vazamento de dados
    """

    # Rotas públicas que NÃO precisam de autenticação/tenant
    PUBLIC_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/tenants/register",  # Registro de novos tenants
        "/api/v1/setup/status",  # Verificar status do setup
        "/api/v1/setup/init",  # Inicializar sistema
        "/api/v1/setup/version",  # Verificar versao do backend
        "/api/v1/setup/diagnostico",  # Diagnostico de dados
        "/api/v1/setup/corrigir-tenant-ids",  # Corrigir tenant_ids
        "/api/v1/version",  # Endpoint de versao simples
        "/api/v1/emails/config/status",  # Verificar config de email
    ]

    # Prefixos de rotas públicas (para rotas dinâmicas)
    PUBLIC_PREFIXES = [
        "/api/v1/emails/teste/",  # Teste de email
        "/api/v1/setup/debug-propostas/",  # Debug propostas
    ]

    async def dispatch(self, request: Request, call_next):
        """
        Processa cada requisição antes de chegar nas rotas
        """
        path = request.url.path

        # Permitir requisições OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Rotas públicas passam direto
        # Inclui arquivos estáticos (assets, imagens, etc)
        # E rotas do frontend SPA (tudo que não começa com /api/)
        is_public_prefix = any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES)
        if (path in self.PUBLIC_PATHS or
            is_public_prefix or
            path.startswith("/static") or
            path.startswith("/assets") or
            path.endswith(".css") or
            path.endswith(".js") or
            path.endswith(".svg") or
            path.endswith(".ico") or
            path.endswith(".png") or
            path.endswith(".jpg") or
            path.endswith(".woff") or
            path.endswith(".woff2") or
            path.endswith(".html") or
            not path.startswith("/api/")):  # Rotas SPA do frontend
            clear_current_tenant_id()
            return await call_next(request)

        # Rotas protegidas: verificar token
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Token de autenticação não fornecido"
            )

        token = auth_header.replace("Bearer ", "")

        try:
            # Decodificar JWT
            payload = decode_access_token(token)

            tenant_id = payload.get("tenant_id")
            user_id = payload.get("user_id")

            if not tenant_id:
                raise HTTPException(
                    status_code=401,
                    detail="Token inválido: tenant não identificado"
                )

            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Token inválido: usuário não identificado"
                )

            # Adicionar ao contexto da request
            request.state.tenant_id = tenant_id
            request.state.user_id = user_id
            request.state.user_tipo = payload.get("tipo")

            # Configurar no ContextVar para acesso global
            set_current_tenant_id(tenant_id)

        except JWTError as e:
            clear_current_tenant_id()
            raise HTTPException(
                status_code=401,
                detail=f"Token inválido: {str(e)}"
            )
        except Exception as e:
            clear_current_tenant_id()
            raise HTTPException(
                status_code=401,
                detail=f"Erro ao processar autenticação: {str(e)}"
            )

        # Processar requisição
        response = await call_next(request)

        # Limpar contexto após requisição
        clear_current_tenant_id()

        return response
