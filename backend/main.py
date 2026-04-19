import json
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from routers import auth, documents, permissions, versions, ai as ai_router
from websocket_manager import manager
import models
import auth as auth_utils

logger = logging.getLogger(__name__)

# Create any new tables (e.g. ai_interactions) without touching existing ones
models.Base.metadata.create_all(bind=engine)


def _ensure_ai_interaction_columns():
    """Add new AIInteraction columns on existing Postgres deployments.

    SQLAlchemy's create_all() does not ALTER existing tables. This is a small,
    idempotent migration that runs once at startup. It no-ops on SQLite because
    the test fixture creates tables from scratch.
    """
    if engine.dialect.name != "postgresql":
        return
    statements = [
        "ALTER TABLE ai_interactions ADD COLUMN IF NOT EXISTS user_action VARCHAR",
        "ALTER TABLE ai_interactions ADD COLUMN IF NOT EXISTS final_text TEXT",
        "ALTER TABLE ai_interactions ADD COLUMN IF NOT EXISTS prompt_text TEXT",
        "ALTER TABLE ai_interactions ADD COLUMN IF NOT EXISTS provider_name VARCHAR",
        "ALTER TABLE ai_interactions ADD COLUMN IF NOT EXISTS model_name VARCHAR",
    ]
    try:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
    except Exception:
        logger.exception("Failed to apply ai_interactions column migration")


_ensure_ai_interaction_columns()

app = FastAPI(title="ColabDoc API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(permissions.router)
app.include_router(versions.router)
app.include_router(ai_router.router)


@app.websocket("/ws/documents/{doc_id}")
async def document_ws(
    websocket: WebSocket,
    doc_id: int,
    token: str = Query(...),
):
    # Authenticate
    user_id = auth_utils.decode_token(token)
    if user_id is None:
        await websocket.close(code=4001)
        return

    db: Session = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            await websocket.close(code=4001)
            return

        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if not doc:
            await websocket.close(code=4004)
            return

        role = auth_utils.get_document_permission(doc, user, db)
        if role is None:
            await websocket.close(code=4003)
            return

        user_info = {"id": user.id, "name": user.name, "role": role}
        await manager.connect(doc_id, websocket, user_info)

        # Send current document state to the new user
        await websocket.send_text(json.dumps({
            "type": "init",
            "content": doc.content,
            "title": doc.title,
            "active_users": manager.active_users(doc_id),
            "role": role,
        }))

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)

                if msg.get("type") == "update" and role in ("editor", "owner"):
                    # Persist to DB
                    new_content = msg.get("content", doc.content)
                    doc.content = new_content
                    doc.updated_at = auth_utils.utc_now()

                    # Auto-save a version every 10 updates (tracked by version count)
                    version_count = (
                        db.query(models.Version)
                        .filter(models.Version.document_id == doc_id)
                        .count()
                    )
                    # Save a version snapshot on demand (when client sends save_version=true)
                    if msg.get("save_version"):
                        next_num = version_count + 1
                        v = models.Version(
                            document_id=doc_id,
                            content=new_content,
                            version_number=next_num,
                            created_by=user.id,
                            created_at=auth_utils.utc_now(),
                        )
                        db.add(v)

                    db.commit()
                    db.refresh(doc)

                    # Broadcast to other users
                    await manager.broadcast(doc_id, {
                        "type": "update",
                        "content": new_content,
                        "user": user_info,
                    }, exclude=websocket)

                elif msg.get("type") == "cursor":
                    # Broadcast cursor position
                    await manager.broadcast(doc_id, {
                        "type": "cursor",
                        "user": user_info,
                        "position": msg.get("position"),
                    }, exclude=websocket)

                elif msg.get("type") == "typing":
                    # Broadcast a lightweight "X is typing" ping.
                    await manager.broadcast(doc_id, {
                        "type": "typing",
                        "user": user_info,
                    }, exclude=websocket)

        except WebSocketDisconnect:
            user_info = manager.disconnect(doc_id, websocket)
            await manager.broadcast(doc_id, {"type": "user_left", "user": user_info})
    finally:
        db.close()


# Serve built React frontend from frontend/dist/
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
