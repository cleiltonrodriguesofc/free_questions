"""
Autenticação simples com sessão assinada via itsdangerous.
"""
import os
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, status

SECRET_KEY: str = os.getenv("JWT_SECRET", "bacen-study-secret-INSECURE-dev-only")
SESSION_COOKIE = "study_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 dias

_serializer = URLSafeTimedSerializer(SECRET_KEY)



def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_session_cookie(user_id: int) -> str:
    return _serializer.dumps({"user_id": user_id})


def decode_session_cookie(token: str) -> dict:
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return {}
from sqlalchemy.orm import Session
from app.core.infrastructure.database.models import UserModel

def get_current_user_id(request: Request, db: Session = None) -> int:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={"Location": "/login"})
    data = decode_session_cookie(token)
    if not data or "user_id" not in data:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={"Location": "/login"})
    user_id = data["user_id"]
    
    if db:
        user = db.query(UserModel).filter_by(id=user_id).first()
        if not user:
            response = HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
            # To clear the cookie in a redirect exception, it's tricky.
            # But we can just return a regular RedirectResponse if we catch it.
            # Actually, we can append Set-Cookie header to the exception.
            response.headers["Set-Cookie"] = f"{SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"
            raise response

    return user_id

def get_optional_user_id(request: Request, db: Session = None) -> int | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    data = decode_session_cookie(token)
    user_id = data.get("user_id")
    if not user_id:
        return None
        
    if db:
        user = db.query(UserModel).filter_by(id=user_id).first()
        if not user:
            # We can't raise a redirect here since it's optional, 
            # but we can return None. The router will then redirect to /login.
            # However, the cookie is still there. To clear it, we could return a specific response, 
            # but since get_optional_user_id just returns int|None, we just return None.
            # The caller will redirect to /login.
            return None
            
    return user_id
