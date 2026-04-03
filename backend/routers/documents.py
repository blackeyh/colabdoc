from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from database import get_db
from config import get_env
import models
import auth as auth_utils

router = APIRouter(prefix="/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    title: str


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[dict] = None


class AssistRequest(BaseModel):
    selected_text: str
    action: str
    context: Optional[str] = None


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


AI_ACTIONS = {"rewrite", "summarize", "translate", "restructure"}


def _local_ai_fallback(action: str, selected_text: str, context: str | None = None) -> str:
    text = selected_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Selected text is required")

    if action == "rewrite":
        return f"Polished version:\n\n{text}"

    if action == "summarize":
        words = text.split()
        preview = " ".join(words[: min(30, len(words))])
        suffix = "..." if len(words) > 30 else ""
        return f"Summary: {preview}{suffix}"

    if action == "translate":
        return f"Translation placeholder:\n\n{text}\n\nSet OPENAI_API_KEY to enable live translation."

    if action == "restructure":
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        if len(sentences) <= 1:
            return f"Restructured version:\n\n- {text}"
        return "Restructured version:\n\n" + "\n".join(f"- {sentence}" for sentence in sentences)

    raise HTTPException(status_code=400, detail="Unsupported AI action")


async def _generate_ai_suggestion(action: str, selected_text: str, context: str | None = None) -> str:
    api_key = get_env("OPENAI_API_KEY")
    model = get_env("OPENAI_MODEL", "gpt-4.1-mini")

    if not api_key:
        return _local_ai_fallback(action, selected_text, context)

    action_instructions = {
        "rewrite": "Rewrite the selected text to be clearer and more polished while preserving meaning.",
        "summarize": "Summarize the selected text concisely.",
        "translate": "Translate the selected text into clear modern English.",
        "restructure": "Restructure the selected text into a more readable format without changing meaning.",
    }
    prompt = (
        f"{action_instructions[action]}\n\n"
        f"Document context:\n{(context or '').strip() or '[none]'}\n\n"
        f"Selected text:\n{selected_text.strip()}\n\n"
        "Return only the transformed text. Do not add commentary or labels."
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": prompt,
                },
            )
        response.raise_for_status()
        data = response.json()
        suggestion = data.get("output_text", "").strip()
        return suggestion or _local_ai_fallback(action, selected_text, context)
    except Exception:
        return _local_ai_fallback(action, selected_text, context)


@router.get("")
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(
    body: CreateDocumentRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if not body.title:
        raise HTTPException(status_code=400, detail="Title is missing")
    now = datetime.utcnow()
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


@router.get("/{doc_id}")
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


@router.put("/{doc_id}")
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
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "title": doc.title, "content": doc.content, "updated_at": doc.updated_at}


@router.delete("/{doc_id}")
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


@router.post("/{doc_id}/ai/assist")
async def ai_assist_document(
    doc_id: int,
    body: AssistRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    _require_access(doc, current_user, db, "viewer")

    action = body.action.strip().lower()
    if action not in AI_ACTIONS:
        raise HTTPException(status_code=400, detail="Unsupported AI action")

    suggestion = await _generate_ai_suggestion(action, body.selected_text, body.context)
    return {"suggestion": suggestion}
