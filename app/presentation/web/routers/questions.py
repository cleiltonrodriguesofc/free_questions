from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.infrastructure.auth import get_current_user_id
from app.core.infrastructure.database.session import get_db
from sqlalchemy.orm import Session
from app.core.application.use_cases.get_questions import GetQuestionsUseCase

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
    user_id = get_current_user_id(request)
    from app.core.infrastructure.database.repositories.question_repo import SqliteUserRepository
    user_repo = SqliteUserRepository(db)
    user = user_repo.get_by_id(user_id)

    use_case = GetQuestionsUseCase(db)
    
    # Get filters
    filter_options = use_case.get_filter_options()
    
    # Get questions
    result = use_case.execute(
        page=page, 
        limit=20, 
        subject_id=subject_id, 
        topic=topic, 
        source=source
    )

    return templates.TemplateResponse(
        "questions.html",
        {
            "request": request,
            "user": user,
            "questions": result["items"],
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "subjects": filter_options["subjects"],
            "sources": filter_options["sources"],
            "topics": filter_options["topics"],
            # Current filters state
            "current_subject_id": subject_id,
            "current_topic": topic,
            "current_source": source
        }
    )
