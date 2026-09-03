import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.infrastructure.database.models import QuestionModel, OptionModel, SubjectModel
from sqlalchemy import func

# Force prod database url
db_url = os.getenv("PROD_DATABASE_URL")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("Testing connection...")
try:
    count = db.query(QuestionModel).count()
    print(f"Total questions: {count}")
    
    print("Testing random query...")
    q = db.query(QuestionModel).order_by(func.random()).limit(1).first()
    print(f"Random question id: {q.id if q else None}")
    
    print("Testing option boolean mapping...")
    opt = db.query(OptionModel).first()
    print(f"Option ID: {opt.id}, is_correct: {opt.is_correct} (type: {type(opt.is_correct)})")

except Exception as e:
    print(f"Error: {e}")

