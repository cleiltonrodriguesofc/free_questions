from abc import ABC, abstractmethod
from typing import Optional
from app.core.domain.entities.question import Question, Subject, User


class IQuestionRepository(ABC):
    @abstractmethod
    def get_by_id(self, question_id: int) -> Optional[Question]: ...

    @abstractmethod
    def list_by_subject(self, subject_id: int, limit: int = 100) -> list[Question]: ...

    @abstractmethod
    def list_random(self, limit: int, subject_id: Optional[int] = None) -> list[Question]: ...

    @abstractmethod
    def count_by_subject(self, subject_id: int) -> int: ...

    @abstractmethod
    def save(self, question: dict) -> Question: ...


class ISubjectRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[Subject]: ...

    @abstractmethod
    def get_by_id(self, subject_id: int) -> Optional[Subject]: ...

    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[Subject]: ...


class IUserRepository(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def create(self, username: str, hashed_password: str) -> User: ...
