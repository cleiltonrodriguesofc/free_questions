import sqlite3
import re

db = 'study.db'
conn = sqlite3.connect(db)
cursor = conn.cursor()

cursor.execute("SELECT id, statement, explanation FROM questions")
rows = cursor.fetchall()

missing_space_punctuation = []
long_words = []
missing_newlines = []

for row in rows:
    q_id, stmt, expl = row
    text = (stmt or '') + " " + (expl or '')
    
    # Check for missing space after comma or period (followed by letter, ignoring numbers like 1.2 or abbreviations like e.g.)
    # Added negative lookbehind/lookahead for numbers to avoid matching 1,5 or 3.14
    if re.search(r'(?<=[a-zA-Z])[.,;:][a-zA-Z]', text):
        missing_space_punctuation.append(q_id)
        
    # Check for unusually long "words" which could be words merged together (e.g. wordswordswords)
    words = text.split()
    if any(len(w) > 30 and not w.startswith('http') and not '/' in w for w in words):
        long_words.append(q_id)
        
    # Check if text is very long but has no newlines
    if len(text) > 500 and '\n' not in text:
        missing_newlines.append(q_id)

print(f"Total questions: {len(rows)}")
print(f"Questions with potential missing spaces after punctuation: {len(missing_space_punctuation)}")
print(f"Questions with suspiciously long words (collapsed spaces): {len(long_words)}")
print(f"Questions with long text but no newlines: {len(missing_newlines)}")

print("\n--- AMOSTRA DE FALTANDO ESPAÇO APÓS PONTUAÇÃO ---")
for q_id in missing_space_punctuation[:3]:
    cursor.execute("SELECT statement FROM questions WHERE id = ?", (q_id,))
    res = cursor.fetchone()[0]
    print(f"ID {q_id}: {res[:200]}...")

print("\n--- AMOSTRA DE PALAVRAS MUITO LONGAS (POSSÍVEL JUNÇÃO) ---")
for q_id in long_words[:3]:
    cursor.execute("SELECT statement FROM questions WHERE id = ?", (q_id,))
    res = cursor.fetchone()[0]
    words = res.split()
    long_w = [w for w in words if len(w) > 30 and not w.startswith('http') and not '/' in w]
    print(f"ID {q_id}: long word(s) = {long_w}")
    print(f"Context: {res[:200]}...")

print("\n--- AMOSTRA SEM QUEBRA DE LINHA (LONGA) ---")
for q_id in missing_newlines[:3]:
    cursor.execute("SELECT statement FROM questions WHERE id = ?", (q_id,))
    res = cursor.fetchone()[0]
    print(f"ID {q_id}: {res[:300]}...")

