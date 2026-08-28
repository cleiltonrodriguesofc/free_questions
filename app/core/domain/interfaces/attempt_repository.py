from abc import ABC, abstractmethod
from typing import Optional
from app.core.domain.entities.attempt import QuizAttempt, AttemptAnswer


class IAttemptRepository(ABC):
    @abstractmethod
    def create_attempt(self, user_id: int, mode: str, subject_id: Optional[int],
                       total_questions: int, time_limit_s: int) -> QuizAttempt: ...

    @abstractmethod
    def save_answer(self, attempt_id: int, question_id: int, selected_label: str,
                    is_correct: bool, time_spent_s: int) -> AttemptAnswer: ...

    @abstractmethod
    def finish_attempt(self, attempt_id: int, correct: int, elapsed_s: int) -> QuizAttempt: ...

    @abstractmethod
    def get_attempt(self, attempt_id: int) -> Optional[QuizAttempt]: ...

    @abstractmethod
    def list_by_user(self, user_id: int, limit: int = 20) -> list[QuizAttempt]: ...

    @abstractmethod
    def get_stats_by_user(self, user_id: int) -> dict: ...

    @abstractmethod
    def get_wrong_questions(self, user_id: int, subject_id: Optional[int] = None) -> list[int]: ...

    @abstractmethod
    def get_stats_by_topic(self, user_id: int, subject_id: Optional[int] = None) -> list[dict]: ...
