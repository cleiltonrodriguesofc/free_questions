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


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_uc(db: Session) -> GetQuizUseCase:
    return GetQuizUseCase(
        SqliteQuestionRepository(db),
        SqliteSubjectRepository(db),
        SqliteAttemptRepository(db),
    )


def _render_quiz(request, result, mode_label, study_mode: bool = False):
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "attempt": result["attempt"],
        "questions": result["questions"],
        "subject": result.get("subject"),
        "mode_label": mode_label,
        "study_mode": study_mode,
    })


# ─── Iniciar simulado por disciplina ─────────────────────────────────────────

@router.get("/subject/{subject_id}", response_class=HTMLResponse)
def start_subject_quiz(
    request: Request,
    subject_id: int,
    review: bool = False,
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(request)
    uc = _make_uc(db)
    try:
        result = uc.execute(user_id=user_id, mode="subject",
                            subject_id=subject_id, review_errors=review)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    label = f"Simulado: {result['subject'].name}" if result["subject"] else "Simulado"
    return _render_quiz(request, result, label, study_mode=True)


# ─── Simulado completo proporcional ──────────────────────────────────────────

@router.get("/exam", response_class=HTMLResponse)
def start_full_exam(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    uc = _make_uc(db)
    try:
        result = uc.execute(user_id=user_id, mode="full_exam")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _render_quiz(request, result, "Simulado Completo — 100 Questões")


# ─── Simulado TCE (preset) ────────────────────────────────────────────────────

@router.get("/tce", response_class=HTMLResponse)
def start_tce_exam(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    uc = _make_uc(db)
    try:
        result = uc.execute(user_id=user_id, mode="tce")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _render_quiz(request, result, "🏛️ Simulado TCE-MA — Formato Real (100q)")


# ─── Simulado customizável ────────────────────────────────────────────────────

@router.get("/custom", response_class=HTMLResponse)
def custom_quiz_form(request: Request, db: Session = Depends(get_db)):
    get_current_user_id(request)
    subject_repo = SqliteSubjectRepository(db)
    question_repo = SqliteQuestionRepository(db)
    subjects = subject_repo.list_all()
    # Enriquecer com contagem real de questões
    for s in subjects:
        s.question_count = question_repo.count_by_subject(s.id)
    return templates.TemplateResponse("quiz_custom.html", {
        "request": request,
        "subjects": subjects,
    })


@router.post("/custom", response_class=HTMLResponse)
def start_custom_quiz(
    request: Request,
    db: Session = Depends(get_db),
    quantities: str = Form(...),   # JSON: {"subject_id": count, ...}
):
    user_id = get_current_user_id(request)
    try:
        raw = json.loads(quantities)
        selections = {int(k): int(v) for k, v in raw.items() if int(v) > 0}
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de seleção inválido")

    uc = _make_uc(db)
    try:
        result = uc.execute(user_id=user_id, mode="custom", selections=selections)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    total = sum(selections.values())
    return _render_quiz(request, result, f"✏️ Simulado Customizado — {total} Questões", study_mode=True)


# ─── Revisão de erros ─────────────────────────────────────────────────────────

@router.get("/review", response_class=HTMLResponse)
def start_review(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    uc = _make_uc(db)
    try:
        result = uc.execute(user_id=user_id, mode="review")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _render_quiz(request, result, "📝 Revisão de Erros", study_mode=True)


# ─── Submeter respostas ───────────────────────────────────────────────────────

@router.post("/submit/{attempt_id}")
def submit_quiz(
    request: Request,
    attempt_id: int,
    answers_json: str = Form(...),
    elapsed_s: int = Form(0),
    db: Session = Depends(get_db),
):
    get_current_user_id(request)
    try:
        raw = json.loads(answers_json)
        answers = {int(k): v for k, v in raw.items()}
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de respostas inválido")

    uc = SubmitQuizUseCase(SqliteQuestionRepository(db), SqliteAttemptRepository(db))
    uc.execute(attempt_id=attempt_id, answers=answers, elapsed_s=elapsed_s)
    return RedirectResponse(f"/result/{attempt_id}", status_code=302)
