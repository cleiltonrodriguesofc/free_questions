import sqlite3
import sys
from pathlib import Path

# Add project root to path to import pdf_extractor
sys.path.insert(0, str(Path(__file__).parent))
from app.core.infrastructure.seeds.pdf_extractor import clean_extracted_text

DB_PATH = 'study.db'

def sanitize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Update questions (statement and explanation)
    print("Sanitizing questions...")
    cursor.execute("SELECT id, statement, explanation FROM questions")
    questions = cursor.fetchall()
    
    q_updates = []
    for q_id, statement, explanation in questions:
        new_statement = clean_extracted_text(statement) if statement else statement
        new_explanation = clean_extracted_text(explanation) if explanation else explanation
        
        if new_statement != statement or new_explanation != explanation:
            q_updates.append((new_statement, new_explanation, q_id))
            
    if q_updates:
        cursor.executemany("UPDATE questions SET statement = ?, explanation = ? WHERE id = ?", q_updates)
        conn.commit()
        print(f"  -> Updated {len(q_updates)} questions.")
    else:
        print("  -> No questions needed update.")

    # 2. Update options (text)
    print("Sanitizing options...")
    cursor.execute("SELECT id, text FROM options")
    options = cursor.fetchall()
    
    opt_updates = []
    for o_id, text in options:
        new_text = clean_extracted_text(text) if text else text
        if new_text != text:
            opt_updates.append((new_text, o_id))
            
    if opt_updates:
        cursor.executemany("UPDATE options SET text = ? WHERE id = ?", opt_updates)
        conn.commit()
        print(f"  -> Updated {len(opt_updates)} options.")
    else:
        print("  -> No options needed update.")

    conn.close()
    print("Sanitization complete.")

if __name__ == "__main__":
    sanitize_database()
