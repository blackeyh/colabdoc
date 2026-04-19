from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


class RegisterResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(TokenPair):
    user: UserResponse


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    summary="Register a new user",
)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if not body.name or not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Missing required fields")
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    user = models.User(
        name=body.name,
        email=body.email,
        password=auth_utils.hash_password(body.password),
        created_at=auth_utils.utc_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return RegisterResponse(id=user.id, name=user.name, email=user.email, created_at=user.created_at)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in and receive access + refresh tokens",
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Missing fields")
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not auth_utils.verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    access, refresh = auth_utils.issue_tokens(user.id)
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse(id=user.id, name=user.name, email=user.email),
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Exchange a refresh token for a new access + refresh pair",
)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    user_id = auth_utils.decode_refresh_token(body.refresh_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    access, refresh_token = auth_utils.issue_tokens(user.id)
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.post("/logout", summary="Stateless logout — client discards tokens")
def logout(current_user: models.User = Depends(auth_utils.get_current_user)):
    # JWT is stateless; client just discards the tokens
    return {"message": "Logged out successfully"}


@router.get("/users/search", summary="Search users by name or email")
def search_users(
    q: str,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    results = (
        db.query(models.User)
        .filter(
            (models.User.name.ilike(f"%{q}%")) | (models.User.email.ilike(f"%{q}%"))
        )
        .filter(models.User.id != current_user.id)
        .limit(10)
        .all()
    )
    return {"users": [{"id": u.id, "name": u.name, "email": u.email} for u in results]}
