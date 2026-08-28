from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.domain.interfaces.attempt_repository import IAttemptRepository
from app.core.domain.entities.attempt import QuizAttempt, AttemptAnswer
from app.core.infrastructure.database.models import (
    QuizAttemptModel, AttemptAnswerModel, QuestionModel, OptionModel, SubjectModel
)


class SqliteAttemptRepository(IAttemptRepository):
    def __init__(self, db: Session):
        self._db = db

    def create_attempt(self, user_id: int, mode: str, subject_id: Optional[int],
                       total_questions: int, time_limit_s: int) -> QuizAttempt:
        m = QuizAttemptModel(
            user_id=user_id,
            mode=mode,
            subject_id=subject_id,
            total_questions=total_questions,
            time_limit_s=time_limit_s,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return self._model_to_entity(m)

    def save_answer(self, attempt_id: int, question_id: int, selected_label: str,
                    is_correct: bool, time_spent_s: int) -> AttemptAnswer:
        m = AttemptAnswerModel(
            attempt_id=attempt_id,
            question_id=question_id,
            selected_label=selected_label,
            is_correct=is_correct,
            time_spent_s=time_spent_s,
        )
        self._db.add(m)
        self._db.commit()
        return AttemptAnswer(
            id=m.id,
            attempt_id=attempt_id,
            question_id=question_id,
            selected_label=selected_label,
            is_correct=is_correct,
            time_spent_s=time_spent_s,
        )

    def finish_attempt(self, attempt_id: int, correct: int, elapsed_s: int) -> QuizAttempt:
        m = self._db.query(QuizAttemptModel).filter_by(id=attempt_id).first()
        m.correct_answers = correct
        m.score_pct = round(correct / m.total_questions * 100, 1) if m.total_questions else 0.0
        m.elapsed_s = elapsed_s
        m.finished_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(m)
        return self._model_to_entity(m)

    def get_attempt(self, attempt_id: int) -> Optional[QuizAttempt]:
        m = self._db.query(QuizAttemptModel).filter_by(id=attempt_id).first()
        if not m:
            return None
        attempt = self._model_to_entity(m)
        answers = []
        for a in m.answers:
            q = self._db.query(QuestionModel).filter_by(id=a.question_id).first()
            correct_opt = next((o for o in q.options if o.is_correct), None) if q else None
            answers.append(AttemptAnswer(
                id=a.id,
                attempt_id=a.attempt_id,
                question_id=a.question_id,
                selected_label=a.selected_label,
                is_correct=a.is_correct,
                time_spent_s=a.time_spent_s,
                question_statement=q.statement if q else "",
                correct_label=correct_opt.label if correct_opt else "",
                explanation=q.explanation if q else "",
                topic=q.topic if q else "",
                needs_review=not a.is_correct,
            ))
        attempt.answers = answers
        return attempt

    def list_by_user(self, user_id: int, limit: int = 20) -> list[QuizAttempt]:
        rows = (
            self._db.query(QuizAttemptModel)
            .filter_by(user_id=user_id)
            .order_by(QuizAttemptModel.started_at.desc())
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(r) for r in rows]

    def get_stats_by_user(self, user_id: int) -> dict:
        """Returns per-subject stats: {subject_id: {name, total, correct, pct}}"""
        rows = (
            self._db.query(QuizAttemptModel)
            .filter_by(user_id=user_id)
            .filter(QuizAttemptModel.finished_at.isnot(None))
            .all()
        )
        stats: dict = {}
        overall_total = 0
        overall_correct = 0
        for r in rows:
            key = r.subject_id or 0
            if key not in stats:
                subj_name = "Simulado Completo"
                if r.subject:
                    subj_name = r.subject.name
                stats[key] = {"name": subj_name, "total": 0, "correct": 0}
            stats[key]["total"] += r.total_questions
            stats[key]["correct"] += r.correct_answers
            overall_total += r.total_questions
            overall_correct += r.correct_answers

        for v in stats.values():
            v["pct"] = round(v["correct"] / v["total"] * 100, 1) if v["total"] else 0.0

        # overall
        overall_pct = round(overall_correct / overall_total * 100, 1) if overall_total else 0.0
        return {
            "by_subject": stats,
            "overall_total": overall_total,
            "overall_correct": overall_correct,
            "overall_pct": overall_pct,
            "attempts_count": len(rows),
        }

    def get_wrong_questions(self, user_id: int, subject_id: Optional[int] = None) -> list[int]:
        """Returns question IDs that the user most recently answered wrong."""
        subq = (
            self._db.query(
                AttemptAnswerModel.question_id,
                func.max(AttemptAnswerModel.id).label("last_id"),
            )
            .join(QuizAttemptModel, QuizAttemptModel.id == AttemptAnswerModel.attempt_id)
            .filter(QuizAttemptModel.user_id == user_id)
        )
        if subject_id:
            subq = subq.filter(QuizAttemptModel.subject_id == subject_id)
        subq = subq.group_by(AttemptAnswerModel.question_id).subquery()

        rows = (
            self._db.query(AttemptAnswerModel)
            .join(subq, AttemptAnswerModel.id == subq.c.last_id)
            .filter(AttemptAnswerModel.is_correct == False)  # noqa: E712
            .all()
        )
        return [r.question_id for r in rows]

    def get_stats_by_topic(self, user_id: int, subject_id: Optional[int] = None) -> list[dict]:
        """
        Retorna desempenho agrupado por tópico (campo topic da Question).
        [{ topic, total, correct, pct }]
        """
        topic_stats: dict[str, dict] = {}

        answers = (
            self._db.query(AttemptAnswerModel)
            .join(QuizAttemptModel, QuizAttemptModel.id == AttemptAnswerModel.attempt_id)
            .filter(QuizAttemptModel.user_id == user_id)
            .all()
        )
        for a in answers:
            q = self._db.query(QuestionModel).filter_by(id=a.question_id).first()
            if not q:
                continue
            if subject_id and q.subject_id != subject_id:
                continue
            topic = q.topic or "Geral"
            if topic not in topic_stats:
                topic_stats[topic] = {"topic": topic, "total": 0, "correct": 0}
            topic_stats[topic]["total"] += 1
            if a.is_correct:
                topic_stats[topic]["correct"] += 1

        result = []
        for v in topic_stats.values():
            v["pct"] = round(v["correct"] / v["total"] * 100, 1) if v["total"] else 0.0
            result.append(v)

        result.sort(key=lambda x: x["pct"])  # mais fracos primeiro
        return result

    # ── helpers ──────────────────────────────────────────────────────────────

    def _model_to_entity(self, m: QuizAttemptModel) -> QuizAttempt:
        subject_name = ""
        if m.subject:
            subject_name = m.subject.name
        return QuizAttempt(
            id=m.id,
            user_id=m.user_id,
            mode=m.mode,
            subject_id=m.subject_id,
            total_questions=m.total_questions,
            correct_answers=m.correct_answers,
            score_pct=m.score_pct,
            time_limit_s=m.time_limit_s,
            elapsed_s=m.elapsed_s,
            started_at=m.started_at,
            finished_at=m.finished_at,
            subject_name=subject_name,
        )
