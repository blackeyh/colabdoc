from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils

router = APIRouter(tags=["versions"])


class VersionSummary(BaseModel):
    id: int
    version_number: int
    created_by: int
    created_at: datetime


class VersionListResponse(BaseModel):
    versions: List[VersionSummary]


class VersionDetailResponse(BaseModel):
    id: int
    document_id: int
    version_number: int
    content: dict
    created_by: int
    created_at: datetime


class RestoredDocument(BaseModel):
    id: int
    title: str
    content: dict
    updated_at: datetime


class RestoreResponse(BaseModel):
    message: str
    document: RestoredDocument


def _get_doc_or_404(doc_id: int, db: Session) -> models.Document:
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _require_access(doc: models.Document, user: models.User, db: Session, min_role: str = "viewer"):
    role = auth_utils.get_document_permission(doc, user, db)
    if role is None:
        raise HTTPException(status_code=403, detail="No permission")
    order = {"viewer": 0, "commenter": 1, "editor": 2, "owner": 3}
    if order.get(role, -1) < order.get(min_role, 0):
        raise HTTPException(status_code=403, detail="Insufficient permission")


@router.get(
    "/documents/{doc_id}/versions",
    response_model=VersionListResponse,
    summary="List version snapshots for a document, newest first",
)
def list_versions(
    doc_id: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    _require_access(doc, current_user, db, "viewer")
    versions = (
        db.query(models.Version)
        .filter(models.Version.document_id == doc_id)
        .order_by(models.Version.version_number.desc())
        .all()
    )
    return {
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "created_by": v.created_by,
                "created_at": v.created_at,
            }
            for v in versions
        ]
    }


@router.get(
    "/documents/{doc_id}/versions/{version_number}",
    response_model=VersionDetailResponse,
    summary="Fetch a specific version snapshot",
)
def get_version(
    doc_id: int,
    version_number: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    _require_access(doc, current_user, db, "viewer")
    version = (
        db.query(models.Version)
        .filter(models.Version.document_id == doc_id, models.Version.version_number == version_number)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "id": version.id,
        "document_id": version.document_id,
        "version_number": version.version_number,
        "content": version.content,
        "created_by": version.created_by,
        "created_at": version.created_at,
    }


@router.post(
    "/documents/{doc_id}/versions/restore/{version_number}",
    response_model=RestoreResponse,
    summary="Restore a document to an earlier version (editor or owner)",
)
def restore_version(
    doc_id: int,
    version_number: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    _require_access(doc, current_user, db, "editor")
    version = (
        db.query(models.Version)
        .filter(models.Version.document_id == doc_id, models.Version.version_number == version_number)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    # Save current state as a new version before restoring
    latest = (
        db.query(models.Version)
        .filter(models.Version.document_id == doc_id)
        .order_by(models.Version.version_number.desc())
        .first()
    )
    next_version_number = (latest.version_number + 1) if latest else 1
    new_version = models.Version(
        document_id=doc_id,
        content=doc.content,
        version_number=next_version_number,
        created_by=current_user.id,
        created_at=auth_utils.utc_now(),
    )
    db.add(new_version)
    doc.content = version.content
    doc.updated_at = auth_utils.utc_now()
    db.commit()
    db.refresh(doc)
    return {
        "message": f"Document restored to version {version_number}",
        "document": {"id": doc.id, "title": doc.title, "content": doc.content, "updated_at": doc.updated_at},
    }
