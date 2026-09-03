from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.infrastructure.database.session import get_db
from app.core.infrastructure.database.repositories.question_repo import SqliteUserRepository
from app.core.infrastructure.auth import (
    hash_password, verify_password,
    create_session_cookie, SESSION_COOKIE, get_optional_user_id
)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/presentation/web/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "", db: Session = Depends(get_db)):
    user_id = get_optional_user_id(request, db)
    if user_id:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    repo = SqliteUserRepository(db)
    user = repo.get_by_username(username.strip())
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuário ou senha incorretos."},
            status_code=401,
        )
    token = create_session_cookie(user.id)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(SESSION_COOKIE, token, max_age=60 * 60 * 24 * 7, httponly=True, samesite="lax")
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    user_id = get_optional_user_id(request, db)
    if user_id:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": ""})


@router.post("/register")
def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    repo = SqliteUserRepository(db)
    if repo.get_by_username(username.strip()):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Nome de usuário já existe."},
            status_code=400,
        )
    hashed = hash_password(password)
    repo.create(username.strip(), hashed)
    return RedirectResponse("/login?registered=1", status_code=302)


@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
