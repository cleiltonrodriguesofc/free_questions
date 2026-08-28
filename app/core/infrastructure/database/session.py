from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.infrastructure.database.models import Base

DATABASE_URL = "sqlite:///./study.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
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
