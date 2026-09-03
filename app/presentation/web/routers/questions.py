from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.infrastructure.auth import get_current_user_id
from app.core.infrastructure.database.session import get_db
from sqlalchemy.orm import Session
from app.core.application.use_cases.get_questions import GetQuestionsUseCase
from app.core.infrastructure.database.repositories.question_repo import (
    SqliteQuestionRepository, SqliteSubjectRepository
)

router = APIRouter(prefix="/questions", tags=["questions"])
templates = Jinja2Templates(directory="app/presentation/web/templates")


@router.get("/", response_class=HTMLResponse)
def list_questions(
    request: Request,
    page: int = Query(1, ge=1),
    subject_id: Optional[int] = Query(None),
    topic: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    get_current_user_id(request, db)

    use_case = GetQuestionsUseCase(db)
    filter_options = use_case.get_filter_options()
    result = use_case.execute(page=page, limit=20, subject_id=subject_id, topic=topic, source=source)

    return templates.TemplateResponse("questions.html", {
        "request": request,
        "questions": result["items"],
        "total": result["total"],
        "page": result["page"],
        "total_pages": result["total_pages"],
        "subjects": filter_options["subjects"],
        "sources": filter_options["sources"],
        "topics": filter_options["topics"],
        "current_subject_id": subject_id,
        "current_topic": topic,
        "current_source": source,
    })


@router.get("/{question_id}", response_class=HTMLResponse)
def question_detail(
    request: Request,
    question_id: int,
    subject_id: Optional[int] = Query(None),
    topic: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Exibe uma questão individualmente com gabarito imediato ao clicar."""
    get_current_user_id(request, db)

    q_repo = SqliteQuestionRepository(db)
    question = q_repo.get_by_id(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    # Busca IDs vizinhos (prev / next) dentro do mesmo filtro
    from app.core.infrastructure.database.models import QuestionModel
    from sqlalchemy import func

    base = db.query(QuestionModel.id)
    if subject_id:
        base = base.filter(QuestionModel.subject_id == subject_id)
    if topic:
        base = base.filter(QuestionModel.topic.ilike(f"%{topic}%"))
    base = base.order_by(QuestionModel.id)
    ids = [row[0] for row in base.all()]

    idx = ids.index(question_id) if question_id in ids else -1
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx >= 0 and idx < len(ids) - 1 else None

    return templates.TemplateResponse("question_detail.html", {
        "request": request,
        "question": question,
        "prev_id": prev_id,
        "next_id": next_id,
        "subject_id": subject_id,
        "topic": topic,
        "total_in_filter": len(ids),
        "position": idx + 1 if idx >= 0 else 0,
    })


@router.get("/api/subjects/{subject_id}/topics")
def get_subject_topics(subject_id: int, db: Session = Depends(get_db)):
    from app.core.infrastructure.database.models import QuestionModel
    topics = [t[0] for t in db.query(QuestionModel.topic).filter(
        QuestionModel.subject_id == subject_id,
        QuestionModel.topic != "",
        QuestionModel.topic.isnot(None)
    ).distinct().all()]
    return {"topics": topics}

class AnswerSubmit(BaseModel):
    selected_label: str

@router.post("/api/questions/{question_id}/check")
def check_question_answer(
    request: Request,
    question_id: int,
    payload: AnswerSubmit,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id(request, db)
    
    from app.core.infrastructure.database.models import QuestionModel, OptionModel, SpacedReviewModel
    
    question = db.query(QuestionModel).filter_by(id=question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Questão não encontrada")
        
    correct_opt = next((o for o in question.options if o.is_correct), None)
    is_correct = (correct_opt is not None and correct_opt.label == payload.selected_label)
    
    # Atualiza ou cria revisão espaçada
    review = db.query(SpacedReviewModel).filter_by(user_id=user_id, question_id=question_id).first()
    
    if not is_correct:
        if not review:
            review = SpacedReviewModel(user_id=user_id, question_id=question_id, interval_days=1)
            db.add(review)
        else:
            review.interval_days = 1
            review.next_review_date = datetime.utcnow() + timedelta(days=1)
    else:
        if review:
            # Acertou na revisão! Aumenta o espaçamento
            intervals = [1, 3, 7, 15, 30]
            try:
                idx = intervals.index(review.interval_days)
                next_interval = intervals[idx+1] if idx + 1 < len(intervals) else 30
            except ValueError:
                next_interval = 3
            review.interval_days = next_interval
            review.next_review_date = datetime.utcnow() + timedelta(days=next_interval)
            
    db.commit()
    
    return JSONResponse({
        "is_correct": is_correct,
        "correct_label": correct_opt.label if correct_opt else None,
        "explanation": question.explanation
    })

