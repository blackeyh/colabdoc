from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils

router = APIRouter(tags=["permissions"])


class GrantPermissionRequest(BaseModel):
    user_id: int
    role: str


class UpdatePermissionRequest(BaseModel):
    role: str


VALID_ROLES = {"editor", "commenter", "viewer"}


def _get_doc_or_404(doc_id: int, db: Session) -> models.Document:
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{doc_id}/permissions")
def list_permissions(
    doc_id: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    role = auth_utils.get_document_permission(doc, current_user, db)
    if role is None:
        raise HTTPException(status_code=403, detail="No permission")
    perms = db.query(models.Permission).filter(models.Permission.document_id == doc_id).all()
    result = []
    for p in perms:
        user = db.query(models.User).filter(models.User.id == p.user_id).first()
        result.append({"user_id": p.user_id, "user_name": user.name if user else "", "role": p.role})
    return {"permissions": result}


@router.post("/documents/{doc_id}/permissions", status_code=201)
def grant_permission(
    doc_id: int,
    body: GrantPermissionRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    if doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the owner")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")
    target_user = db.query(models.User).filter(models.User.id == body.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own permission as owner")
    existing = (
        db.query(models.Permission)
        .filter(models.Permission.document_id == doc_id, models.Permission.user_id == body.user_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already has permission")
    perm = models.Permission(user_id=body.user_id, document_id=doc_id, role=body.role)
    db.add(perm)
    db.commit()
    return {"user_id": perm.user_id, "document_id": perm.document_id, "role": perm.role}


@router.put("/documents/{doc_id}/permissions/{user_id}")
def update_permission(
    doc_id: int,
    user_id: int,
    body: UpdatePermissionRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    if doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the owner")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")
    perm = (
        db.query(models.Permission)
        .filter(models.Permission.document_id == doc_id, models.Permission.user_id == user_id)
        .first()
    )
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    perm.role = body.role
    db.commit()
    return {"user_id": perm.user_id, "document_id": perm.document_id, "role": perm.role}


@router.delete("/documents/{doc_id}/permissions/{user_id}")
def revoke_permission(
    doc_id: int,
    user_id: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    if doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the owner")
    perm = (
        db.query(models.Permission)
        .filter(models.Permission.document_id == doc_id, models.Permission.user_id == user_id)
        .first()
    )
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    db.delete(perm)
    db.commit()
    return {"message": "Access removed successfully"}
