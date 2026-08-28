"""
BACEN Study Simulator
FastAPI + Clean Architecture + Jinja2 + SQLite
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.infrastructure.database.session import init_db
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


@app.get("/health")
def health():
    return {"status": "ok"}
