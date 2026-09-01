"""
Use case: Montar um simulado por disciplina, customizável ou modo prova completa.
"""
from typing import Optional
from app.core.domain.interfaces.repositories import IQuestionRepository, ISubjectRepository
from app.core.domain.interfaces.attempt_repository import IAttemptRepository
from app.core.domain.entities.question import Question, Subject
from app.core.domain.entities.attempt import QuizAttempt

# ── Configurações padrão ──────────────────────────────────────────────────────
FULL_EXAM_QUESTIONS = 100
FULL_EXAM_TIME_S    = 4 * 60 * 60   # 4 horas

SUBJECT_QUIZ_QUESTIONS = 10
SUBJECT_QUIZ_TIME_S    = 30 * 60    # 30 minutos

# Preset TCE — distribuição por subject_id (preencha com os IDs reais do banco).
# Deixe vazio ({}) para distribuição automática proporcional.
TCE_PRESET: dict[int, int] = {}
TCE_TOTAL_QUESTIONS = 100
TCE_TIME_S = 4 * 60 * 60  # 4 horas


class GetQuizUseCase:
    def __init__(
        self,
        question_repo: IQuestionRepository,
        subject_repo: ISubjectRepository,
        attempt_repo: IAttemptRepository,
    ):
        self._questions = question_repo
        self._subjects  = subject_repo
        self._attempts  = attempt_repo

    def execute(
        self,
        user_id: int,
        mode: str,
        subject_id: Optional[int] = None,
        review_errors: bool = False,
        selections: Optional[dict[int, int]] = None,
        topic: Optional[str] = None,  # filtro de tópico para modo subject
    ) -> dict:
        """
        mode: "subject" | "full_exam" | "review" | "custom" | "tce"
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
                questions = self._questions.list_random(
                    SUBJECT_QUIZ_QUESTIONS,
                    subject_id=subject_id,
                    topic=topic,
                )
            time_limit = SUBJECT_QUIZ_TIME_S

        elif mode == "full_exam":
            # Distribui proporcionalmente pelas disciplinas com questões disponíveis
            questions = self._build_proportional(FULL_EXAM_QUESTIONS)
            time_limit = FULL_EXAM_TIME_S

        elif mode == "tce":
            if TCE_PRESET:
                questions = self._questions.list_random_multi(TCE_PRESET)
            else:
                # Sem preset configurado: distribuição proporcional
                questions = self._build_proportional(TCE_TOTAL_QUESTIONS)
            time_limit = TCE_TIME_S

        elif mode == "custom":
            if not selections:
                raise ValueError("'selections' obrigatório no modo custom")
            total = sum(selections.values())
            if total == 0:
                raise ValueError("Selecione ao menos 1 questão")
            questions = self._questions.list_random_multi(selections)
            time_limit = max(30 * 60, total * 90)  # 90s por questão, mínimo 30min

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

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_proportional(self, total: int) -> list[Question]:
        """Distribui `total` questões proporcionalmente entre as disciplinas disponíveis."""
        subjects = self._subjects.list_all()
        available = [(s, self._questions.count_by_subject(s.id)) for s in subjects if self._questions.count_by_subject(s.id) > 0]
        if not available:
            return []
        grand_total = sum(cnt for _, cnt in available)
        selections: dict[int, int] = {}
        distributed = 0
        for s, cnt in available[:-1]:
            n = max(1, round(total * cnt / grand_total))
            n = min(n, cnt)
            selections[s.id] = n
            distributed += n
        # última disciplina recebe o restante
        last_s, last_cnt = available[-1]
        remainder = max(0, total - distributed)
        selections[last_s.id] = min(remainder, last_cnt)
        return self._questions.list_random_multi(selections)
