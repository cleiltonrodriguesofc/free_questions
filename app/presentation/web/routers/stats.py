from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.infrastructure.database.session import get_db
from app.core.infrastructure.database.repositories.question_repo import (
    SqliteSubjectRepository, SqliteUserRepository
)
from app.core.infrastructure.database.repositories.attempt_repo import SqliteAttemptRepository
from app.core.infrastructure.auth import get_current_user_id
from app.core.application.use_cases.get_stats import GetStatsUseCase

router = APIRouter(prefix="/stats", tags=["stats"])
templates = Jinja2Templates(directory="app/presentation/web/templates")


@router.get("", response_class=HTMLResponse)
def stats_page(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = SqliteUserRepository(db).get_by_id(user_id)
    subject_repo = SqliteSubjectRepository(db)
    attempt_repo = SqliteAttemptRepository(db)

    stats_uc = GetStatsUseCase(attempt_repo, subject_repo)
    stats = stats_uc.execute(user_id)

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "user": user,
        "stats": stats,
    })
