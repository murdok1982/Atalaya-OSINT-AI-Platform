from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self._active_connections: dict[str, list[WebSocket]] = {}
        self._user_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "general", user_id: str = "") -> None:
        await websocket.accept()
        if channel not in self._active_connections:
            self._active_connections[channel] = []
        self._active_connections[channel].append(websocket)
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = []
            self._user_connections[user_id].append(websocket)
        logger.info("websocket_connected", channel=channel, user_id=user_id, total=len(self._active_connections.get(channel, [])))

    def disconnect(self, websocket: WebSocket, channel: str = "general", user_id: str = "") -> None:
        if channel in self._active_connections:
            if websocket in self._active_connections[channel]:
                self._active_connections[channel].remove(websocket)
        if user_id and user_id in self._user_connections:
            if websocket in self._user_connections[user_id]:
                self._user_connections[user_id].remove(websocket)
        logger.info("websocket_disconnected", channel=channel, user_id=user_id)

    async def broadcast(self, channel: str, message: dict[str, Any]) -> int:
        sent = 0
        connections = self._active_connections.get(channel, [])
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
                sent += 1
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in connections:
                connections.remove(conn)
        return sent

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> int:
        sent = 0
        connections = self._user_connections.get(user_id, [])
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
                sent += 1
            except Exception:
                pass
        return sent

    async def send_job_update(self, job_id: str, status: str, progress: float = 0.0, data: dict[str, Any] | None = None) -> None:
        message = {
            "type": "job_update",
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "data": data or {},
            "timestamp": __import__("time").time(),
        }
        await self.broadcast(f"job:{job_id}", message)
        await self.broadcast("jobs", message)

    async def send_alert(self, alert_type: str, message: str, severity: str = "info", data: dict[str, Any] | None = None) -> None:
        alert = {
            "type": "alert",
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "data": data or {},
            "timestamp": __import__("time").time(),
        }
        await self.broadcast("alerts", alert)

    async def send_evidence_update(self, case_id: str, evidence_id: str, action: str) -> None:
        message = {
            "type": "evidence_update",
            "case_id": case_id,
            "evidence_id": evidence_id,
            "action": action,
            "timestamp": __import__("time").time(),
        }
        await self.broadcast(f"case:{case_id}", message)
        await self.broadcast("evidence", message)

    def get_active_count(self, channel: str = "") -> int:
        if channel:
            return len(self._active_connections.get(channel, []))
        return sum(len(conns) for conns in self._active_connections.values())

    def get_stats(self) -> dict[str, Any]:
        return {
            "channels": {ch: len(conns) for ch, conns in self._active_connections.items()},
            "users": len(self._user_connections),
            "total_connections": self.get_active_count(),
        }


websocket_manager = WebSocketManager()
