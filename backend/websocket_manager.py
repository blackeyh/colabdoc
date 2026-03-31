"""
WebSocket room manager for real-time document collaboration.

Each document has a room. When a user connects, they receive the current document
state from the DB. Every content update is broadcast to all other users in the same room.
"""
import json
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # doc_id -> set of (websocket, user_info) tuples
        self.rooms: Dict[int, list] = {}

    def _get_room(self, doc_id: int) -> list:
        if doc_id not in self.rooms:
            self.rooms[doc_id] = []
        return self.rooms[doc_id]

    async def connect(self, doc_id: int, websocket: WebSocket, user_info: dict):
        await websocket.accept()
        self._get_room(doc_id).append({"ws": websocket, "user": user_info})
        # Notify others that a user joined
        await self.broadcast(doc_id, {"type": "user_joined", "user": user_info}, exclude=websocket)

    def disconnect(self, doc_id: int, websocket: WebSocket):
        room = self._get_room(doc_id)
        user_info = None
        for conn in room:
            if conn["ws"] is websocket:
                user_info = conn["user"]
                break
        self.rooms[doc_id] = [c for c in room if c["ws"] is not websocket]
        if not self.rooms[doc_id]:
            del self.rooms[doc_id]
        return user_info

    async def broadcast(self, doc_id: int, message: dict, exclude: WebSocket = None):
        room = self._get_room(doc_id)
        dead = []
        for conn in room:
            if conn["ws"] is exclude:
                continue
            try:
                await conn["ws"].send_text(json.dumps(message))
            except Exception:
                dead.append(conn)
        for d in dead:
            self.rooms[doc_id].remove(d)

    def active_users(self, doc_id: int) -> list:
        return [c["user"] for c in self._get_room(doc_id)]


manager = ConnectionManager()
