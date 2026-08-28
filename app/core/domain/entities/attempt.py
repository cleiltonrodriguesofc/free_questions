from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AttemptAnswer:
    id: int
    attempt_id: int
    question_id: int
    selected_label: str        # A, B, C, D ou E
    is_correct: bool
    time_spent_s: int = 0
    question_statement: str = ""
    correct_label: str = ""
    explanation: str = ""
    topic: str = ""            # tópico da questão para stats por conteúdo
    needs_review: bool = False  # marcado quando errado → revisão futura


@dataclass
class QuizAttempt:
    id: int
    user_id: int
    mode: str                  # "subject" | "full_exam"
    subject_id: Optional[int]
    total_questions: int
    correct_answers: int = 0
    score_pct: float = 0.0
    time_limit_s: int = 0      # 0 = sem limite
    elapsed_s: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    answers: list = field(default_factory=list)
    subject_name: str = ""
