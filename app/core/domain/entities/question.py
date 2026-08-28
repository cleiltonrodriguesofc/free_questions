from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    username: str
    hashed_password: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Subject:
    id: int
    name: str
    slug: str
    phase: str   # "Phase 1 - Foundation", "Phase 2 - IT Pipeline", "Phase 3 - Domain Backlog"
    day: int
    description: str = ""
    question_count: int = 0


@dataclass
class Option:
    id: int
    question_id: int
    label: str   # A, B, C, D, E
    text: str
    is_correct: bool = False


@dataclass
class Question:
    id: int
    subject_id: int
    statement: str
    explanation: str = ""
    difficulty: str = "médio"   # fácil, médio, difícil
    source: str = ""            # ex: "BACEN 2021", "Cebraspe 2022"
    year: Optional[int] = None
    topic: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    options: list = field(default_factory=list)
    subject: Optional["Subject"] = None
