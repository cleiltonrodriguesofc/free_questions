"""
Script de exportação: SQLite → JSON para importação no Supabase/PostgreSQL.
Gera um arquivo 'db_export.json' com todos os dados do banco.

Uso:
    python3 export_db.py
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "study.db"
OUTPUT_PATH = Path(__file__).parent / "db_export.json"


def serialize(value):
    """Converte tipos não-serializáveis para JSON."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def export_table(cursor: sqlite3.Cursor, table: str) -> list[dict]:
    cursor.execute(f"SELECT * FROM {table}")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, [serialize(v) for v in row])) for row in rows]


def main():
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado em: {DB_PATH}")
        return

    print(f"📂 Conectando ao banco: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Ordem respeitando FK: primeiro pais, depois filhos
    tables_order = [
        "users",
        "subjects",
        "questions",
        "options",
        "quiz_attempts",
        "attempt_answers",
    ]

    export = {}
    total_rows = 0

    for table in tables_order:
        try:
            rows = export_table(cursor, table)
            export[table] = rows
            print(f"  ✅ {table}: {len(rows)} registros")
            total_rows += len(rows)
        except sqlite3.OperationalError as e:
            print(f"  ⚠️  {table}: {e}")
            export[table] = []

    conn.close()

    output = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "source": "SQLite (study.db)",
        "total_rows": total_rows,
        "tables": export,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\n✅ Exportação concluída!")
    print(f"   Arquivo: {OUTPUT_PATH}")
    print(f"   Tamanho: {size_mb:.2f} MB")
    print(f"   Total de registros: {total_rows}")


if __name__ == "__main__":
    main()
