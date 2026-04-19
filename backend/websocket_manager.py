"""
WebSocket room manager for real-time document collaboration.

Each document has a room. When a user connects, they receive the current document
state from the DB plus the latest live collaboration snapshot, if available.
"""
import json
from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[int, dict] = {}

    def _get_room(self, doc_id: int) -> dict:
        if doc_id not in self.rooms:
            self.rooms[doc_id] = {"connections": [], "snapshot": None}
        return self.rooms[doc_id]

    def _connections(self, doc_id: int) -> list:
        return self._get_room(doc_id)["connections"]

    async def connect(self, doc_id: int, websocket: WebSocket, user_info: dict):
        await websocket.accept()
        self._connections(doc_id).append({"ws": websocket, "user": user_info})
        # Notify others that a user joined
        await self.broadcast(doc_id, {"type": "user_joined", "user": user_info}, exclude=websocket)

    def disconnect(self, doc_id: int, websocket: WebSocket):
        room = self._get_room(doc_id)
        connections = room["connections"]
        user_info = None
        for conn in connections:
            if conn["ws"] is websocket:
                user_info = conn["user"]
                break
        room["connections"] = [c for c in connections if c["ws"] is not websocket]
        if not room["connections"]:
            del self.rooms[doc_id]
        return user_info

    async def broadcast(self, doc_id: int, message: dict, exclude: WebSocket = None):
        room = self._connections(doc_id)
        dead = []
        for conn in room:
            if conn["ws"] is exclude:
                continue
            try:
                await conn["ws"].send_text(json.dumps(message))
            except Exception:
                dead.append(conn)
        for d in dead:
            if d in room:
                room.remove(d)

    async def send_to_user(self, doc_id: int, user_id: int, message: dict):
        room = self._connections(doc_id)
        dead = []
        for conn in room:
            if conn["user"].get("id") != user_id:
                continue
            try:
                await conn["ws"].send_text(json.dumps(message))
            except Exception:
                dead.append(conn)
        for d in dead:
            if d in room:
                room.remove(d)

    def active_users(self, doc_id: int) -> list:
        return [c["user"] for c in self._connections(doc_id)]

    def snapshot(self, doc_id: int) -> str | None:
        return self._get_room(doc_id)["snapshot"]

    def set_snapshot(self, doc_id: int, snapshot: str | None):
        self._get_room(doc_id)["snapshot"] = snapshot


manager = ConnectionManager()
