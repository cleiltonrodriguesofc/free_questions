"""
Use case: Montar um simulado por disciplina ou modo prova completa.
"""
from typing import Optional
from app.core.domain.interfaces.repositories import IQuestionRepository, ISubjectRepository
from app.core.domain.interfaces.attempt_repository import IAttemptRepository
from app.core.domain.entities.question import Question, Subject
from app.core.domain.entities.attempt import QuizAttempt

# Configurações do simulado completo estilo prova
FULL_EXAM_QUESTIONS = 20
FULL_EXAM_TIME_S = 60 * 60  # 60 minutos
SUBJECT_QUIZ_QUESTIONS = 10
SUBJECT_QUIZ_TIME_S = 30 * 60  # 30 minutos


class GetQuizUseCase:
    def __init__(
        self,
        question_repo: IQuestionRepository,
        subject_repo: ISubjectRepository,
        attempt_repo: IAttemptRepository,
    ):
        self._questions = question_repo
        self._subjects = subject_repo
        self._attempts = attempt_repo

    def execute(
        self,
        user_id: int,
        mode: str,
        subject_id: Optional[int] = None,
        review_errors: bool = False,
    ) -> dict:
        """
        mode: "subject" | "full_exam" | "review"
        Returns: {"attempt": QuizAttempt, "questions": list[Question], "subject": Subject|None}
        """
        subject: Optional[Subject] = None
        time_limit = 0

        if mode == "subject":
            if not subject_id:
                raise ValueError("subject_id obrigatório no modo 'subject'")
            subject = self._subjects.get_by_id(subject_id)
            if not subject:
                raise ValueError("Disciplina não encontrada")
            if review_errors:
                wrong_ids = self._attempts.get_wrong_questions(user_id, subject_id)
                questions = [self._questions.get_by_id(qid) for qid in wrong_ids[:SUBJECT_QUIZ_QUESTIONS]]
                questions = [q for q in questions if q]
            else:
                questions = self._questions.list_random(SUBJECT_QUIZ_QUESTIONS, subject_id=subject_id)
            time_limit = SUBJECT_QUIZ_TIME_S

        elif mode == "full_exam":
            questions = self._questions.list_random(FULL_EXAM_QUESTIONS)
            time_limit = FULL_EXAM_TIME_S

        elif mode == "review":
            wrong_ids = self._attempts.get_wrong_questions(user_id)
            questions = [self._questions.get_by_id(qid) for qid in wrong_ids[:SUBJECT_QUIZ_QUESTIONS]]
            questions = [q for q in questions if q]
            time_limit = SUBJECT_QUIZ_TIME_S

        else:
            raise ValueError(f"Modo desconhecido: {mode}")

        if not questions:
            raise ValueError("Nenhuma questão disponível para este simulado.")

        attempt = self._attempts.create_attempt(
            user_id=user_id,
            mode=mode,
            subject_id=subject_id,
            total_questions=len(questions),
            time_limit_s=time_limit,
        )

        return {"attempt": attempt, "questions": questions, "subject": subject}
