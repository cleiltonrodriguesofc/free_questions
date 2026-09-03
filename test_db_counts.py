import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.infrastructure.database.models import QuestionModel, OptionModel, SubjectModel, UserModel, QuizAttemptModel, AttemptAnswerModel

db_url = os.getenv("PROD_DATABASE_URL")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("Counts:")
print(f"Users: {db.query(UserModel).count()}")
print(f"Subjects: {db.query(SubjectModel).count()}")
print(f"Questions: {db.query(QuestionModel).count()}")
print(f"Options: {db.query(OptionModel).count()}")
print(f"Quiz Attempts: {db.query(QuizAttemptModel).count()}")
print(f"Attempt Answers: {db.query(AttemptAnswerModel).count()}")
