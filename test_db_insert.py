import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.infrastructure.database.models import QuizAttemptModel, UserModel
from datetime import datetime

db_url = os.getenv("PROD_DATABASE_URL")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("Testing attempt insert...")
try:
    user = db.query(UserModel).first()
    if not user:
        print("No users found.")
    else:
        attempt = QuizAttemptModel(
            user_id=user.id,
            mode="test",
            total_questions=10,
            time_limit_s=60,
            started_at=datetime.utcnow()
        )
        db.add(attempt)
        db.commit()
        print(f"Inserted attempt with ID: {attempt.id}")
except Exception as e:
    print(f"Error: {e}")

