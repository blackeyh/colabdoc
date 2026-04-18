import logging
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from database import get_db
import models
import auth as auth_utils
from ai import build_prompt, get_provider, truncate_context, VALID_ACTIONS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai"])


class AIAssistRequest(BaseModel):
    selected_text: str
    action: str
    context: Optional[str] = None


class AIAssistResponse(BaseModel):
    id: int
    action: str
    suggestion: str
    status: str


class AIResolveRequest(BaseModel):
    user_action: Literal["accepted", "rejected", "edited"]
    edited_text: Optional[str] = None


class AIResolveResponse(BaseModel):
    id: int
    user_action: str
    final_text: Optional[str] = None


class AIHistoryEntry(BaseModel):
    id: int
    action: Optional[str]
    selected_text: str
    suggestion: Optional[str]
    status: Optional[str]
    user_action: Optional[str]
    final_text: Optional[str]
    created_at: Optional[str]


class AIHistoryResponse(BaseModel):
    history: list[AIHistoryEntry]
    total: int


def _get_doc_or_404(doc_id: int, db: Session) -> models.Document:
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _extract_document_text(content) -> str:
    """Best-effort: extract plain text from either legacy {text:""} or Tiptap JSON."""
    if not content:
        return ""
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        parts: list[str] = []

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "text" and isinstance(node.get("text"), str):
                    parts.append(node["text"])
                for child in node.get("content", []) or []:
                    walk(child)

        walk(content)
        return "\n".join(parts)
    if isinstance(content, str):
        return content
    return ""


@router.post(
    "/documents/{doc_id}/ai/assist",
    response_model=AIAssistResponse,
    summary="Request an AI suggestion for selected text",
)
def ai_assist(
    doc_id: int,
    body: AIAssistRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if not body.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text must not be empty")
    if body.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"action must be one of: {sorted(VALID_ACTIONS)}")

    doc = _get_doc_or_404(doc_id, db)
    role = auth_utils.get_document_permission(doc, current_user, db)
    if role is None:
        raise HTTPException(status_code=403, detail="No permission")

    # Build context from the document itself if the client didn't supply one.
    raw_context = body.context if body.context is not None else _extract_document_text(doc.content)
    context = truncate_context(raw_context, body.selected_text)

    interaction = models.AIInteraction(
        document_id=doc_id,
        user_id=current_user.id,
        action=body.action,
        selected_text=body.selected_text,
        status="pending",
        user_action="pending",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    prompt = build_prompt(body.action, body.selected_text, context)
    try:
        suggestion = get_provider().complete(prompt)
    except ClientDisconnect:
        interaction.status = "cancelled"
        db.commit()
        raise
    except Exception as exc:
        logger.exception("AI provider error")
        interaction.status = "failed"
        db.commit()
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    interaction.suggestion = suggestion
    interaction.status = "completed"
    db.commit()
    return AIAssistResponse(id=interaction.id, action=body.action, suggestion=suggestion, status="completed")


@router.post(
    "/documents/{doc_id}/ai/interactions/{interaction_id}/resolve",
    response_model=AIResolveResponse,
    summary="Log the user's decision on an AI suggestion",
)
def ai_resolve(
    doc_id: int,
    interaction_id: int,
    body: AIResolveRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    interaction = (
        db.query(models.AIInteraction)
        .filter(
            models.AIInteraction.id == interaction_id,
            models.AIInteraction.document_id == doc_id,
        )
        .first()
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    if interaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your interaction")

    interaction.user_action = body.user_action
    if body.user_action == "edited":
        interaction.final_text = body.edited_text or interaction.suggestion
    elif body.user_action == "accepted":
        interaction.final_text = interaction.suggestion
    else:
        interaction.final_text = None
    db.commit()
    return AIResolveResponse(
        id=interaction.id,
        user_action=interaction.user_action,
        final_text=interaction.final_text,
    )


@router.get(
    "/documents/{doc_id}/ai/history",
    response_model=AIHistoryResponse,
    summary="List AI interactions for the current user on this document",
)
def ai_history(
    doc_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    role = auth_utils.get_document_permission(doc, current_user, db)
    if role is None:
        raise HTTPException(status_code=403, detail="No permission")

    base = (
        db.query(models.AIInteraction)
        .filter(
            models.AIInteraction.document_id == doc_id,
            models.AIInteraction.user_id == current_user.id,
        )
    )
    total = base.count()
    interactions = (
        base.order_by(models.AIInteraction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AIHistoryResponse(
        history=[
            AIHistoryEntry(
                id=i.id,
                action=i.action,
                selected_text=(i.selected_text or "")[:200],
                suggestion=i.suggestion,
                status=i.status,
                user_action=i.user_action,
                final_text=i.final_text,
                created_at=i.created_at.isoformat() if i.created_at else None,
            )
            for i in interactions
        ],
        total=total,
    )
