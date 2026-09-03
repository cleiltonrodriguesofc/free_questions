from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempts = relationship("QuizAttemptModel", back_populates="user")


class SubjectModel(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    phase = Column(String(60), nullable=False)
    day = Column(Integer, nullable=False)
    description = Column(Text, default="")

    questions = relationship("QuestionModel", back_populates="subject")
    attempts = relationship("QuizAttemptModel", back_populates="subject")


class QuestionModel(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    statement = Column(Text, nullable=False)
    explanation = Column(Text, default="")
    difficulty = Column(String(20), default="médio")
    source = Column(String(120), default="")
    year = Column(Integer, nullable=True)
    topic = Column(String(120), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("SubjectModel", back_populates="questions")
    options = relationship("OptionModel", back_populates="question", cascade="all, delete-orphan")
    answers = relationship("AttemptAnswerModel", back_populates="question")


class OptionModel(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    label = Column(String(1), nullable=False)   # A, B, C, D, E
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("QuestionModel", back_populates="options")


class QuizAttemptModel(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    mode = Column(String(20), nullable=False)          # subject | full_exam
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, default=0)
    score_pct = Column(Float, default=0.0)
    time_limit_s = Column(Integer, default=0)
    elapsed_s = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("UserModel", back_populates="attempts")
    subject = relationship("SubjectModel", back_populates="attempts")
    answers = relationship("AttemptAnswerModel", back_populates="attempt", cascade="all, delete-orphan")


class AttemptAnswerModel(Base):
    __tablename__ = "attempt_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_label = Column(String(1), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_spent_s = Column(Integer, default=0)

    attempt = relationship("QuizAttemptModel", back_populates="answers")
    question = relationship("QuestionModel", back_populates="answers")

class SpacedReviewModel(Base):
    __tablename__ = "spaced_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    interval_days = Column(Integer, default=1)
    next_review_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserModel")
    question = relationship("QuestionModel")
