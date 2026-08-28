from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.core.domain.interfaces.repositories import (
    IQuestionRepository, ISubjectRepository, IUserRepository
)
from app.core.domain.entities.question import Question, Option, Subject, User
from app.core.infrastructure.database.models import (
    QuestionModel, OptionModel, SubjectModel, UserModel
)


# ─── Question Repository ─────────────────────────────────────────────────────

class SqliteQuestionRepository(IQuestionRepository):
    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, m: QuestionModel) -> Question:
        opts = [
            Option(id=o.id, question_id=o.question_id, label=o.label,
                   text=o.text, is_correct=o.is_correct)
            for o in sorted(m.options, key=lambda x: x.label)
        ]
        q = Question(
            id=m.id,
            subject_id=m.subject_id,
            statement=m.statement,
            explanation=m.explanation or "",
            difficulty=m.difficulty or "médio",
            source=m.source or "",
            year=m.year,
            topic=m.topic or "",
            created_at=m.created_at,
            options=opts,
        )
        if m.subject:
            q.subject = Subject(
                id=m.subject.id,
                name=m.subject.name,
                slug=m.subject.slug,
                phase=m.subject.phase,
                day=m.subject.day,
                description=m.subject.description or "",
            )
        return q

    def get_by_id(self, question_id: int) -> Optional[Question]:
        m = self._db.query(QuestionModel).filter_by(id=question_id).first()
        return self._to_entity(m) if m else None

    def list_by_subject(self, subject_id: int, limit: int = 100) -> list[Question]:
        rows = (
            self._db.query(QuestionModel)
            .filter_by(subject_id=subject_id)
            .limit(limit)
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def list_random(self, limit: int, subject_id: Optional[int] = None) -> list[Question]:
        q = self._db.query(QuestionModel)
        if subject_id:
            q = q.filter_by(subject_id=subject_id)
        rows = q.order_by(func.random()).limit(limit).all()
        return [self._to_entity(r) for r in rows]

    def count_by_subject(self, subject_id: int) -> int:
        return self._db.query(func.count(QuestionModel.id)).filter_by(subject_id=subject_id).scalar() or 0

    def save(self, data: dict) -> Question:
        opts_data = data.pop("options", [])
        m = QuestionModel(**data)
        self._db.add(m)
        self._db.flush()
        for o in opts_data:
            self._db.add(OptionModel(question_id=m.id, **o))
        self._db.commit()
        self._db.refresh(m)
        return self._to_entity(m)


# ─── Subject Repository ───────────────────────────────────────────────────────

class SqliteSubjectRepository(ISubjectRepository):
    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, m: SubjectModel) -> Subject:
        count = self._db.query(func.count(QuestionModel.id)).filter_by(subject_id=m.id).scalar() or 0
        return Subject(
            id=m.id, name=m.name, slug=m.slug,
            phase=m.phase, day=m.day,
            description=m.description or "",
            question_count=count,
        )

    def list_all(self) -> list[Subject]:
        rows = self._db.query(SubjectModel).order_by(SubjectModel.phase, SubjectModel.day).all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, subject_id: int) -> Optional[Subject]:
        m = self._db.query(SubjectModel).filter_by(id=subject_id).first()
        return self._to_entity(m) if m else None

    def get_by_slug(self, slug: str) -> Optional[Subject]:
        m = self._db.query(SubjectModel).filter_by(slug=slug).first()
        return self._to_entity(m) if m else None


# ─── User Repository ──────────────────────────────────────────────────────────

class SqliteUserRepository(IUserRepository):
    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, m: UserModel) -> User:
        return User(id=m.id, username=m.username, hashed_password=m.hashed_password, created_at=m.created_at)

    def get_by_username(self, username: str) -> Optional[User]:
        m = self._db.query(UserModel).filter_by(username=username).first()
        return self._to_entity(m) if m else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        m = self._db.query(UserModel).filter_by(id=user_id).first()
        return self._to_entity(m) if m else None

    def create(self, username: str, hashed_password: str) -> User:
        m = UserModel(username=username, hashed_password=hashed_password)
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return self._to_entity(m)
