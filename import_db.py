import json
import os
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, unquote

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv()

# ── Configuração ──────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("PROD_DATABASE_URL")
if not DATABASE_URL:
    print("❌ Defina a variável PROD_DATABASE_URL antes de rodar.")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

EXPORT_FILE = Path(__file__).parent / "db_export.json"

# ── Engine com parâmetros explícitos (evita problemas com @ na senha) ─────────
parsed = urlparse(DATABASE_URL)
_connect_args = {
    "host": parsed.hostname,
    "port": parsed.port or 5432,
    "dbname": parsed.path.lstrip("/"),
    "user": unquote(parsed.username or ""),
    "password": unquote(parsed.password or ""),
    "sslmode": "require",
    "connect_timeout": 15,
}

def _creator():
    import psycopg2
    return psycopg2.connect(**_connect_args)

engine = create_engine("postgresql+psycopg2://", creator=_creator, pool_pre_ping=True)

Session = sessionmaker(bind=engine)


def parse_dt(value: str | None):
    """Converte string ISO para datetime, ou None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def load_export() -> dict:
    if not EXPORT_FILE.exists():
        print(f"❌ Arquivo não encontrado: {EXPORT_FILE}")
        sys.exit(1)
    with open(EXPORT_FILE, encoding="utf-8") as f:
        return json.load(f)


def create_tables():
    """Cria todas as tabelas usando os models SQLAlchemy."""
    from app.core.infrastructure.database.models import Base
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas/verificadas no Supabase")
    except Exception as e:
        if "already exists" in str(e):
            print("⚠️  Tabelas já existem — seguindo para importação")
        else:
            raise



def import_table(table: str, rows: list[dict], batch_size: int = 100):
    """Usa uma transação por batch para evitar timeout do session pooler."""
    if not rows:
        print(f"  ⏭️  {table}: vazio, pulando")
        return 0

    columns = list(rows[0].keys())
    col_str = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    sql = text(
        f'INSERT INTO {table} ({col_str}) VALUES ({placeholders}) '
        f'ON CONFLICT DO NOTHING'
    )

    inserted = 0
    total_batches = (len(rows) + batch_size - 1) // batch_size
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        batch_num = i // batch_size + 1
        with engine.begin() as conn:          # transação própria por batch
            conn.execute(sql, batch)
        inserted += len(batch)
        print(f"    [{table}] batch {batch_num}/{total_batches} — {inserted}/{len(rows)}", end="\r")

    print(f"  ✅ {table}: {inserted} registros importados           ")
    return inserted


def reset_sequences(tables_with_id: list[str]):
    """Ajusta sequences para evitar conflito de PK em futuros inserts."""
    with engine.begin() as conn:
        for table in tables_with_id:
            conn.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE(MAX(id), 1)) FROM {table}"
            ))
    print("✅ Sequences ajustadas")


def main():
    print("📂 Carregando db_export.json...")
    data = load_export()
    tables = data.get("tables", {})

    print(f"   Exportado em: {data.get('exported_at')}")
    print(f"   Total de registros: {data.get('total_rows')}\n")

    # 1. Cria tabelas
    create_tables()

    # 2. Importa na ordem correta (FK) — cada batch usa sua própria transação
    order = ["users", "subjects", "questions", "options", "quiz_attempts", "attempt_answers"]
    print("\n📥 Importando dados...")
    for table in order:
        rows = tables.get(table, [])
        import_table(table, rows)

    # 3. Ajusta sequences do PostgreSQL
    print("\n🔧 Ajustando sequences...")
    reset_sequences(["users", "subjects", "questions", "options", "quiz_attempts", "attempt_answers"])

    print("\n🎉 Importação concluída com sucesso!")
    print(f"   Banco: {DATABASE_URL.split('@')[1]}")  # host sem senha


if __name__ == "__main__":
    main()

