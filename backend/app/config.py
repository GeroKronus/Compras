from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """
    Configurações da aplicação
    Carregadas do arquivo .env
    """
    # Database
    DATABASE_URL: str = "postgresql://compras_user:compras_pass_2024@localhost:5432/compras_db"

    # JWT
    SECRET_KEY: str = "sua-chave-secreta-muito-forte-aqui-min-32-caracteres-importante"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 525600  # 1 ano (365 dias)

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Sistema de Compras Multi-Tenant"
    ENVIRONMENT: str = "development"

    # CORS (string separada por vírgula ou lista)
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000"

    # Anthropic AI
    ANTHROPIC_API_KEY: str = ""

    # Email (SMTP/IMAP - Zoho Mail)
    SMTP_HOST: str = "smtppro.zoho.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    IMAP_HOST: str = "imappro.zoho.com"
    IMAP_PORT: int = 993

    # Jobs
    ENABLE_SCHEDULED_JOBS: bool = True  # Habilitado por padrao em producao

    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        json_schema_extra = {
            "json_loads": lambda x: x  # Não fazer parse automático de JSON
        }


settings = Settings()
