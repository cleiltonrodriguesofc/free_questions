from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.infrastructure.database.session import get_db
from app.core.infrastructure.database.repositories.attempt_repo import SqliteAttemptRepository
from app.core.infrastructure.auth import get_current_user_id

router = APIRouter(tags=["results"])
templates = Jinja2Templates(directory="app/presentation/web/templates")


@router.get("/result/{attempt_id}", response_class=HTMLResponse)
def show_result(request: Request, attempt_id: int, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request, db)
    attempt_repo = SqliteAttemptRepository(db)
    attempt = attempt_repo.get_attempt(attempt_id)

    if not attempt or attempt.user_id != user_id:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")

    return templates.TemplateResponse("result.html", {
        "request": request,
        "attempt": attempt,
    })
