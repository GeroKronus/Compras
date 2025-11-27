from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Engine do SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexões antes de usar
    echo=True if settings.ENVIRONMENT == "development" else False  # Log SQL em dev
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os models
Base = declarative_base()


def get_db():
    """
    Dependency para obter sessão do banco de dados
    Usado no FastAPI Depends
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
