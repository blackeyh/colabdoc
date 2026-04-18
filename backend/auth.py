from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from config import get_env
import models

JWT_SECRET = get_env("JWT_SECRET", "fallback-secret")
JWT_ALGORITHM = get_env("JWT_ALGORITHM", "HS256")
JWT_ACCESS_MINUTES = int(get_env("JWT_ACCESS_MINUTES", get_env("JWT_EXPIRE_MINUTES", "20")))
JWT_REFRESH_DAYS = int(get_env("JWT_REFRESH_DAYS", "7"))

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_MINUTES)
    return _encode({"sub": str(user_id), "exp": expire, "type": TOKEN_TYPE_ACCESS})


def create_refresh_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_DAYS)
    return _encode({"sub": str(user_id), "exp": expire, "type": TOKEN_TYPE_REFRESH})


def issue_tokens(user_id: int) -> Tuple[str, str]:
    return create_access_token(user_id), create_refresh_token(user_id)


def _decode(token: str, expected_type: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def decode_token(token: str) -> Optional[int]:
    return _decode(token, TOKEN_TYPE_ACCESS)


def decode_refresh_token(token: str) -> Optional[int]:
    return _decode(token, TOKEN_TYPE_REFRESH)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_document_permission(
    doc: models.Document,
    user: models.User,
    db: Session,
) -> Optional[str]:
    """Return the user's effective role on the document, or None if no access."""
    if doc.owner_id == user.id:
        return "owner"
    perm = (
        db.query(models.Permission)
        .filter(models.Permission.document_id == doc.id, models.Permission.user_id == user.id)
        .first()
    )
    return perm.role if perm else None
