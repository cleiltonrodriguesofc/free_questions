from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.infrastructure.database.session import get_db
from app.core.infrastructure.database.repositories.question_repo import (
    SqliteSubjectRepository, SqliteUserRepository
)
from app.core.infrastructure.database.repositories.attempt_repo import SqliteAttemptRepository
from app.core.infrastructure.auth import get_optional_user_id
from app.core.application.use_cases.get_stats import GetStatsUseCase

router = APIRouter(tags=["home"])
templates = Jinja2Templates(directory="app/presentation/web/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user_id = get_optional_user_id(request, db)
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user_repo = SqliteUserRepository(db)
    user = user_repo.get_by_id(user_id)

    subject_repo = SqliteSubjectRepository(db)
    attempt_repo = SqliteAttemptRepository(db)

    subjects = subject_repo.list_all()
    stats_uc = GetStatsUseCase(attempt_repo, subject_repo)
    stats = stats_uc.execute(user_id)

    from app.core.infrastructure.database.models import SpacedReviewModel
    from datetime import datetime
    pending_reviews = db.query(SpacedReviewModel).filter(
        SpacedReviewModel.user_id == user_id,
        SpacedReviewModel.next_review_date <= datetime.utcnow()
    ).count()

    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user,
        "subjects": subjects,
        "stats": stats,
        "pending_reviews": pending_reviews,
    })
