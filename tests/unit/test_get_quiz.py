import pytest
from app.core.application.use_cases.get_quiz import GetQuizUseCase
from app.core.domain.entities.question import Question, Subject
from app.core.domain.entities.attempt import QuizAttempt
from datetime import datetime

class MockQuestionRepo:
    def count_by_subject(self, subject_id: int) -> int:
        return 50

    def list_random_multi(self, selections: dict[int, int]) -> list[Question]:
        res = []
        for sid, count in selections.items():
            for _ in range(count):
                res.append(Question(id=1, subject_id=sid, statement="test", options=[], topic="", source="", year=2026, explanation=""))
        return res

class MockSubjectRepo:
    def list_all(self) -> list[Subject]:
        return [Subject(id=1, name="Subj 1", slug="subj-1", phase="1", day=1), Subject(id=2, name="Subj 2", slug="subj-2", phase="1", day=2)]

    def get_by_id(self, subject_id: int) -> Subject:
        return Subject(id=subject_id, name=f"Subj {subject_id}", slug=f"subj-{subject_id}", phase="1", day=subject_id)

class MockAttemptRepo:
    def create_attempt(self, user_id, mode, subject_id, total_questions, time_limit_s) -> QuizAttempt:
        return QuizAttempt(id=1, user_id=user_id, mode=mode, subject_id=subject_id, 
                           total_questions=total_questions, correct_answers=0, score_pct=0.0, 
                           time_limit_s=time_limit_s, elapsed_s=0, started_at=datetime.utcnow(), 
                           finished_at=None, subject_name="")

def test_get_quiz_custom():
    uc = GetQuizUseCase(MockQuestionRepo(), MockSubjectRepo(), MockAttemptRepo())
    selections = {1: 5, 2: 3}
    result = uc.execute(user_id=1, mode="custom", selections=selections)
    
    assert result["attempt"].mode == "custom"
    assert result["attempt"].total_questions == 8
    assert len(result["questions"]) == 8

def test_get_quiz_full_exam():
    uc = GetQuizUseCase(MockQuestionRepo(), MockSubjectRepo(), MockAttemptRepo())
    result = uc.execute(user_id=1, mode="full_exam")
    
    assert result["attempt"].mode == "full_exam"
    assert result["attempt"].total_questions == 100
    assert len(result["questions"]) == 100

def test_get_quiz_tce():
    uc = GetQuizUseCase(MockQuestionRepo(), MockSubjectRepo(), MockAttemptRepo())
    # By default, without TCE_PRESET configured, it uses proportional (same as full_exam)
    result = uc.execute(user_id=1, mode="tce")
    
    assert result["attempt"].mode == "tce"
    assert result["attempt"].total_questions == 100
    assert len(result["questions"]) == 100
