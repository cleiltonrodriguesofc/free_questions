import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.infrastructure.database.models import Base

# Lê do ambiente; fallback para SQLite local em desenvolvimento
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./study.db")

# Supabase/Render expõem URLs com prefixo "postgres://", mas SQLAlchemy 2.x
# exige "postgresql://". Corrige automaticamente.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_is_sqlite = DATABASE_URL.startswith("sqlite")

# Parâmetros específicos de cada banco
_connect_args = {"check_same_thread": False, "timeout": 15} if _is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,  # detecta conexões mortas (útil no Supabase)
)


@event.listens_for(Engine, "connect")
def _configure_connection(dbapi_connection, connection_record):
    """Aplica PRAGMAs de performance apenas no SQLite."""
    if _is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Cria todas as tabelas se não existirem."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency injection do FastAPI para sessão de banco."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

