import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils

router = APIRouter(tags=["ai"])

VALID_ACTIONS = {"rewrite", "summarize", "translate", "restructure"}


class AIAssistRequest(BaseModel):
    selected_text: str
    action: str
    context: Optional[str] = None


def _get_doc_or_404(doc_id: int, db: Session) -> models.Document:
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _build_prompt(action: str, selected_text: str, context: Optional[str]) -> str:
    context_block = f"\n\nDocument context:\n{context}" if context else ""
    prompts = {
        "summarize": (
            "Summarize the following text concisely, preserving key points and meaning."
            f"{context_block}\n\nText to summarize:\n{selected_text}\n\n"
            "Provide only the summary, no preamble."
        ),
        "rewrite": (
            "Rewrite the following text to improve clarity, flow, and style while preserving "
            "the original meaning and tone."
            f"{context_block}\n\nText to rewrite:\n{selected_text}\n\n"
            "Provide only the rewritten text, no preamble."
        ),
        "translate": (
            "Translate the following text to English. If it is already in English, translate "
            "it to Spanish."
            f"{context_block}\n\nText to translate:\n{selected_text}\n\n"
            "Provide only the translation, no preamble."
        ),
        "restructure": (
            "Restructure the following text to improve its organization and logical flow. "
            "Use appropriate headings, bullet points, or paragraphs as needed."
            f"{context_block}\n\nText to restructure:\n{selected_text}\n\n"
            "Provide only the restructured text, no preamble."
        ),
    }
    return prompts.get(action, f"Process the following text according to '{action}':\n{selected_text}")


def _call_ai(action: str, selected_text: str, context: Optional[str]) -> str:
    from openai import OpenAI

    prompt = _build_prompt(action, selected_text, context)
    base_url = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    model = os.getenv("LM_STUDIO_MODEL", "local-model")

    client = OpenAI(base_url=base_url, api_key="lm-studio")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return response.choices[0].message.content


@router.post("/documents/{doc_id}/ai/assist")
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

    interaction = models.AIInteraction(
        document_id=doc_id,
        user_id=current_user.id,
        action=body.action,
        selected_text=body.selected_text,
        status="pending",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    try:
        suggestion = _call_ai(body.action, body.selected_text, body.context)
        interaction.suggestion = suggestion
        interaction.status = "completed"
    except Exception as exc:
        interaction.status = "failed"
        db.commit()
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    db.commit()
    return {
        "id": interaction.id,
        "action": body.action,
        "suggestion": suggestion,
        "status": "completed",
    }


@router.get("/documents/{doc_id}/ai/history")
def ai_history(
    doc_id: int,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(doc_id, db)
    role = auth_utils.get_document_permission(doc, current_user, db)
    if role is None:
        raise HTTPException(status_code=403, detail="No permission")

    interactions = (
        db.query(models.AIInteraction)
        .filter(
            models.AIInteraction.document_id == doc_id,
            models.AIInteraction.user_id == current_user.id,
        )
        .order_by(models.AIInteraction.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "history": [
            {
                "id": i.id,
                "action": i.action,
                "selected_text": (i.selected_text or "")[:100],
                "suggestion": i.suggestion,
                "status": i.status,
                "created_at": i.created_at,
            }
            for i in interactions
        ]
    }
