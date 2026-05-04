# ScholarLab/backend/app/services/websocket.py
"""
Faculty WebSocket Connection Manager
=====================================
Manages real-time connections keyed by *session_id* (one active lecture session
per faculty member). Separate from the student ConnectionManager in
`routers/websockets.py` which is keyed by *user_id*.

Pydantic schemas defined here mirror the TypeScript interfaces in
`frontend/src/types/websocket.ts` — keep both in sync.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Literal, Optional

from fastapi import WebSocket
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event Schemas  (mirror TypeScript interfaces in frontend/src/types/websocket.ts)
# ---------------------------------------------------------------------------

class AttendanceVerifiedEvent(BaseModel):
    """Emitted when a student successfully clears the full verification pipeline."""
    type: Literal["attendance_verified"] = "attendance_verified"
    student_id: str
    student_name: str
    session_id: str
    timestamp: str  # ISO 8601 — serialized from datetime
    attendance_count: int


class SpoofingAttemptEvent(BaseModel):
    """Emitted when a spoofing/biometric failure is detected for a session."""
    type: Literal["spoofing_attempt_detected"] = "spoofing_attempt_detected"
    session_id: str
    attempted_at: str  # ISO 8601
    reason: str


class RiskScoreUpdatedEvent(BaseModel):
    """Emitted after an ML risk re-evaluation for an individual student."""
    type: Literal["risk_score_updated"] = "risk_score_updated"
    student_id: str
    new_risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_label: Literal["Safe", "At Risk", "Critical"]


FacultyWSEvent = AttendanceVerifiedEvent | SpoofingAttemptEvent | RiskScoreUpdatedEvent


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Faculty Connection Manager
# ---------------------------------------------------------------------------

class FacultyConnectionManager:
    """
    Tracks one active WebSocket connection per ``session_id``.

    Typical session lifecycle:
        Faculty opens dashboard  ──► connect(ws, session_id)
        Student marks attendance ──► broadcast_to_session(session_id, event)
        Faculty closes browser   ──► disconnect(session_id)  [via WebSocketDisconnect]
    """

    def __init__(self) -> None:
        # session_id → active WebSocket
        self._connections: Dict[str, WebSocket] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self._connections[session_id] = websocket
        logger.info("Faculty WS connected  session_id=%s  total=%d",
                    session_id, len(self._connections))

    def disconnect(self, session_id: str) -> None:
        removed = self._connections.pop(session_id, None)
        if removed is not None:
            logger.info("Faculty WS disconnected  session_id=%s  total=%d",
                        session_id, len(self._connections))

    # ------------------------------------------------------------------
    # Broadcast helpers
    # ------------------------------------------------------------------

    async def broadcast_to_session(
        self,
        session_id: str,
        event: FacultyWSEvent,
    ) -> None:
        """Send an event to the faculty watching a specific session."""
        ws = self._connections.get(session_id)
        if ws is None:
            logger.debug(
                "broadcast_to_session: no active connection for session_id=%s — skipping",
                session_id,
            )
            return
        try:
            await ws.send_json(event.model_dump())
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "broadcast_to_session failed  session_id=%s  error=%s",
                session_id, exc,
            )
            self.disconnect(session_id)

    async def broadcast_to_all(self, event: FacultyWSEvent) -> None:
        """Fan-out an event to every connected faculty WebSocket (e.g. global alerts)."""
        if not self._connections:
            return
        payload = event.model_dump()
        dead: list[str] = []
        for sid, ws in list(self._connections.items()):
            try:
                await ws.send_json(payload)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "broadcast_to_all failed  session_id=%s  error=%s", sid, exc
                )
                dead.append(sid)
        for sid in dead:
            self.disconnect(sid)

    # ------------------------------------------------------------------
    # Convenience factory helpers
    # ------------------------------------------------------------------

    def make_attendance_verified(
        self,
        *,
        student_id: str,
        student_name: str,
        session_id: str,
        attendance_count: int,
    ) -> AttendanceVerifiedEvent:
        return AttendanceVerifiedEvent(
            student_id=student_id,
            student_name=student_name,
            session_id=session_id,
            timestamp=_utc_now_iso(),
            attendance_count=attendance_count,
        )

    def make_spoofing_attempt(
        self,
        *,
        session_id: str,
        reason: str,
    ) -> SpoofingAttemptEvent:
        return SpoofingAttemptEvent(
            session_id=session_id,
            attempted_at=_utc_now_iso(),
            reason=reason,
        )

    def make_risk_score_updated(
        self,
        *,
        student_id: str,
        new_risk_score: float,
        risk_label: Literal["Safe", "At Risk", "Critical"],
    ) -> RiskScoreUpdatedEvent:
        return RiskScoreUpdatedEvent(
            student_id=student_id,
            new_risk_score=new_risk_score,
            risk_label=risk_label,
        )


# ---------------------------------------------------------------------------
# Singleton — import this in routers/ws.py and routers/attendance.py
# ---------------------------------------------------------------------------

faculty_manager = FacultyConnectionManager()
