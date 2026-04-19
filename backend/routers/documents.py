from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from typing import Literal, Optional, List
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from exporters import document_to_html, document_to_plain_text, export_filename

router = APIRouter(prefix="/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    title: str


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[dict] = None


class DocumentSummary(BaseModel):
    id: int
    title: str
    owner_id: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: List[DocumentSummary]


class DocumentResponse(BaseModel):
    id: int
    title: str
    content: dict
    owner_id: int
    created_at: datetime
    updated_at: datetime


class DocumentUpdateResponse(BaseModel):
    id: int
    title: str
    content: dict
    updated_at: datetime


class DeleteResponse(BaseModel):
    message: str


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
    return role


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents owned by or shared with the current user",
)
def list_documents(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    # Documents owned by user
    owned = db.query(models.Document).filter(models.Document.owner_id == current_user.id).all()
    # Documents shared with user
    shared_perms = (
        db.query(models.Permission)
        .filter(models.Permission.user_id == current_user.id)
        .all()
    )
    shared_ids = {p.document_id for p in shared_perms}
    shared = db.query(models.Document).filter(models.Document.id.in_(shared_ids)).all() if shared_ids else []

    all_docs = {d.id: d for d in owned + shared}
    return {
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "owner_id": d.owner_id,
                "created_at": d.created_at,
                "updated_at": d.updated_at,
            }
            for d in all_docs.values()
        ]
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentResponse,
    summary="Create a new document owned by the current user",
)
def create_document(
    body: CreateDocumentRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if not body.title:
        raise HTTPException(status_code=400, detail="Title is missing")
    now = auth_utils.utc_now()
    doc = models.Document(
        title=body.title,
        content={},
        owner_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "owner_id": doc.owner_id,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.get(
    "/{doc_id}",
    response_model=DocumentResponse,
    summary="Fetch a single document the user can access",
)
def get_document(
    doc_id: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    _require_access(doc, current_user, db, "viewer")
    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "owner_id": doc.owner_id,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.get(
    "/{doc_id}/export",
    summary="Export a document as HTML or plain text",
)
def export_document(
    doc_id: int,
    format: Literal["html", "txt"] = Query("html"),
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    _require_access(doc, current_user, db, "viewer")

    title = doc.title or f"Document {doc.id}"
    if format == "txt":
        content = document_to_plain_text(title, doc.content)
        media_type = "text/plain; charset=utf-8"
    else:
        content = document_to_html(title, doc.content)
        media_type = "text/html; charset=utf-8"

    filename = export_filename(title, format, fallback=f"document-{doc.id}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)


@router.put(
    "/{doc_id}",
    response_model=DocumentUpdateResponse,
    summary="Update a document's title and/or content (editor or owner)",
)
def update_document(
    doc_id: int,
    body: UpdateDocumentRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    _require_access(doc, current_user, db, "editor")
    if body.title is not None:
        doc.title = body.title
    if body.content is not None:
        doc.content = body.content
    doc.updated_at = auth_utils.utc_now()
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "title": doc.title, "content": doc.content, "updated_at": doc.updated_at}


@router.delete(
    "/{doc_id}",
    response_model=DeleteResponse,
    summary="Delete a document (owner only)",
)
def delete_document(
    doc_id: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    if doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the owner")
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}
