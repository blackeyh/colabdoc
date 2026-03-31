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


@router.post("/register", status_code=status.HTTP_201_CREATED)
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
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Missing fields")
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not auth_utils.verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    token = auth_utils.create_token(user.id)
    return {"token": token, "user": {"id": user.id, "name": user.name, "email": user.email}}


@router.post("/logout")
def logout(current_user: models.User = Depends(auth_utils.get_current_user)):
    # JWT is stateless; client just discards the token
    return {"message": "Logged out successfully"}


@router.get("/users/search")
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
