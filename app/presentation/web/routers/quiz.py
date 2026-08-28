import json
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.infrastructure.database.session import get_db
from app.core.infrastructure.database.repositories.question_repo import (
    SqliteQuestionRepository, SqliteSubjectRepository
)
from app.core.infrastructure.database.repositories.attempt_repo import SqliteAttemptRepository
from app.core.infrastructure.auth import get_current_user_id
from app.core.application.use_cases.get_quiz import GetQuizUseCase
from app.core.application.use_cases.submit_quiz import SubmitQuizUseCase

router = APIRouter(prefix="/quiz", tags=["quiz"])
templates = Jinja2Templates(directory="app/presentation/web/templates")


# ─── Iniciar simulado por disciplina ─────────────────────────────────────────

@router.get("/subject/{subject_id}", response_class=HTMLResponse)
def start_subject_quiz(
    request: Request,
    subject_id: int,
    review: bool = False,
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(request)

    uc = GetQuizUseCase(
        SqliteQuestionRepository(db),
        SqliteSubjectRepository(db),
        SqliteAttemptRepository(db),
    )
    try:
        result = uc.execute(user_id=user_id, mode="subject", subject_id=subject_id, review_errors=review)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "attempt": result["attempt"],
        "questions": result["questions"],
        "subject": result["subject"],
        "mode_label": f"Simulado: {result['subject'].name}" if result["subject"] else "Simulado",
    })


# ─── Iniciar simulado completo (estilo prova) ─────────────────────────────────

@router.get("/exam", response_class=HTMLResponse)
def start_full_exam(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)

    uc = GetQuizUseCase(
        SqliteQuestionRepository(db),
        SqliteSubjectRepository(db),
        SqliteAttemptRepository(db),
    )
    try:
        result = uc.execute(user_id=user_id, mode="full_exam")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "attempt": result["attempt"],
        "questions": result["questions"],
        "subject": None,
        "mode_label": "Simulado Completo — Estilo Prova",
    })


# ─── Iniciar revisão de erros ─────────────────────────────────────────────────

@router.get("/review", response_class=HTMLResponse)
def start_review(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)

    uc = GetQuizUseCase(
        SqliteQuestionRepository(db),
        SqliteSubjectRepository(db),
        SqliteAttemptRepository(db),
    )
    try:
        result = uc.execute(user_id=user_id, mode="review")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "attempt": result["attempt"],
        "questions": result["questions"],
        "subject": None,
        "mode_label": "Revisão de Erros",
    })


# ─── Submeter respostas ───────────────────────────────────────────────────────

@router.post("/submit/{attempt_id}")
def submit_quiz(
    request: Request,
    attempt_id: int,
    answers_json: str = Form(...),
    elapsed_s: int = Form(0),
    db: Session = Depends(get_db),
):
    get_current_user_id(request)  # garante autenticação
    try:
        raw = json.loads(answers_json)
        answers = {int(k): v for k, v in raw.items()}
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de respostas inválido")

    uc = SubmitQuizUseCase(SqliteQuestionRepository(db), SqliteAttemptRepository(db))
    uc.execute(attempt_id=attempt_id, answers=answers, elapsed_s=elapsed_s)

    return RedirectResponse(f"/result/{attempt_id}", status_code=302)
