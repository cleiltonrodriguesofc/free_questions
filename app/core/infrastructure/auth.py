"""
Autenticação simples com sessão assinada via itsdangerous.
"""
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, status

SECRET_KEY = "bacen-study-secret-key-change-in-prod"
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


def get_current_user_id(request: Request) -> int:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={"Location": "/login"})
    data = decode_session_cookie(token)
    if not data or "user_id" not in data:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={"Location": "/login"})
    return data["user_id"]


def get_optional_user_id(request: Request) -> int | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    data = decode_session_cookie(token)
    return data.get("user_id")
