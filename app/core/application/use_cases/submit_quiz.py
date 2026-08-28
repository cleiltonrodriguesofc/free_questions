"""
Use case: Submeter respostas de um simulado e calcular resultado.
"""
from app.core.domain.interfaces.repositories import IQuestionRepository
from app.core.domain.interfaces.attempt_repository import IAttemptRepository
from app.core.domain.entities.attempt import QuizAttempt


class SubmitQuizUseCase:
    def __init__(self, question_repo: IQuestionRepository, attempt_repo: IAttemptRepository):
        self._questions = question_repo
        self._attempts = attempt_repo

    def execute(self, attempt_id: int, answers: dict[int, str], elapsed_s: int) -> QuizAttempt:
        """
        answers: {question_id: selected_label}
        Retorna QuizAttempt finalizado com score.
        """
        correct_count = 0

        for question_id, selected_label in answers.items():
            question = self._questions.get_by_id(question_id)
            if not question:
                continue

            correct_opt = next((o for o in question.options if o.is_correct), None)
            is_correct = correct_opt is not None and correct_opt.label == selected_label.upper()
            if is_correct:
                correct_count += 1

            self._attempts.save_answer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_label=selected_label.upper(),
                is_correct=is_correct,
                time_spent_s=0,
            )

        return self._attempts.finish_attempt(attempt_id, correct_count, elapsed_s)
