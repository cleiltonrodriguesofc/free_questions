"""
Use case: Estatísticas de desempenho do usuário.
"""
from app.core.domain.interfaces.attempt_repository import IAttemptRepository
from app.core.domain.interfaces.repositories import ISubjectRepository


class GetStatsUseCase:
    def __init__(self, attempt_repo: IAttemptRepository, subject_repo: ISubjectRepository):
        self._attempts = attempt_repo
        self._subjects = subject_repo

    def execute(self, user_id: int) -> dict:
        """
        Retorna dict com:
        - overall_pct, overall_total, overall_correct, attempts_count
        - by_subject: list com name, total, correct, pct para cada disciplina
        - recent_attempts: últimas 10 tentativas
        - weak_subjects: top 3 disciplinas com menor acerto
        """
        stats = self._attempts.get_stats_by_user(user_id)
        recent = self._attempts.list_by_user(user_id, limit=10)

        # enriquecer by_subject com nome correto da disciplina
        all_subjects = {s.id: s.name for s in self._subjects.list_all()}
        by_subject_list = []
        for subj_id, v in stats["by_subject"].items():
            name = all_subjects.get(subj_id, v["name"])
            by_subject_list.append({
                "subject_id": subj_id,
                "name": name,
                "total": v["total"],
                "correct": v["correct"],
                "pct": v["pct"],
            })

        by_subject_list.sort(key=lambda x: x["pct"])

        return {
            "overall_pct": stats["overall_pct"],
            "overall_total": stats["overall_total"],
            "overall_correct": stats["overall_correct"],
            "attempts_count": stats["attempts_count"],
            "by_subject": by_subject_list,
            "weak_subjects": by_subject_list[:3],
            "recent_attempts": recent,
            "by_topic": self._attempts.get_stats_by_topic(user_id),
        }
