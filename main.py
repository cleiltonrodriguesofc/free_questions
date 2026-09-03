"""
BACEN Study Simulator
FastAPI + Clean Architecture + Jinja2 + SQLite/PostgreSQL
"""
from dotenv import load_dotenv
load_dotenv()  # carrega .env em desenvolvimento local (no-op em produção)

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from sqlalchemy import text
from app.core.infrastructure.database.session import init_db, get_db
from app.presentation.web.routers import auth, home, quiz, results, stats, questions

app = FastAPI(title="BACEN Study Simulator", version="1.0.0", docs_url=None, redoc_url=None)

# Static files
app.mount("/static", StaticFiles(directory="app/presentation/static"), name="static")

# Routers
app.include_router(auth.router)
app.include_router(home.router)
app.include_router(quiz.router)
app.include_router(results.router)
app.include_router(stats.router)
app.include_router(questions.router)


@app.on_event("startup")
def startup():
    init_db()


@app.api_route("/health", methods=["GET", "HEAD"])
def health(db = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
