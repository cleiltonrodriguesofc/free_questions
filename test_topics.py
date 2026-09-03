import sqlite3

def check_db():
    conn = sqlite3.connect('study.db')
    cursor = conn.cursor()
    
    # Check topics stats
    query = """
    SELECT topic, COUNT(*) as count 
    FROM questions 
    WHERE topic IS NOT NULL AND topic != '' AND topic != 'Geral'
    GROUP BY topic 
    ORDER BY count DESC 
    LIMIT 15
    """
    topics = cursor.execute(query).fetchall()
    print("--- TOP 15 TÓPICOS ENCONTRADOS ---")
    for t, c in topics:
        print(f"{t}: {c} questões")
    
    print("\n--- AMOSTRA DE QUESTÕES (Tópico x Enunciado) ---")
    query_samples = """
    SELECT s.name as subject, q.topic, q.statement 
    FROM questions q
    JOIN subjects s ON s.id = q.subject_id
    WHERE q.topic IS NOT NULL AND q.topic != '' AND q.topic != 'Geral'
    ORDER BY RANDOM() 
    LIMIT 10
    """
    samples = cursor.execute(query_samples).fetchall()
    for subj, topic, stmt in samples:
        print(f"\n[Disciplina]: {subj}")
        print(f"[Tópico Detectado]: {topic}")
        print(f"[Enunciado (início)]: {stmt[:150]}...")
        
    # Check how many are still "Geral" or empty
    query_empty = "SELECT COUNT(*) FROM questions WHERE topic IS NULL OR topic = '' OR topic = 'Geral'"
    empty_count = cursor.execute(query_empty).fetchone()[0]
    total_count = cursor.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    
    print(f"\n--- ESTATÍSTICAS GERAIS ---")
    print(f"Total de questões: {total_count}")
    print(f"Questões SEM tópico específico ('Geral' ou vazio): {empty_count} ({(empty_count/total_count)*100:.1f}%)")
    print(f"Questões COM tópico específico: {total_count - empty_count} ({((total_count - empty_count)/total_count)*100:.1f}%)")

if __name__ == "__main__":
    check_db()
