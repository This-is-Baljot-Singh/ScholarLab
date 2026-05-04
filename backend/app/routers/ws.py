# ScholarLab/backend/app/routers/ws.py
"""
Faculty WebSocket Router
=========================
Endpoint: ws://localhost:8000/ws/faculty/{session_id}?token=<JWT>

Authentication:
    JWT is passed as a query parameter `token` (identical pattern to the
    existing student WebSocket at /api/ws/student).

Authorization:
    Only `faculty` and `admin` roles are permitted; students are rejected
    with close code 1008 (Policy Violation).

Connection lifecycle:
    • On connect  : registered in FacultyConnectionManager
    • During life  : kept alive via `receive_text()` — client may send pings
    • On disconnect: cleaned up automatically via WebSocketDisconnect
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from app.database import settings, users_collection
from app.services.websocket import faculty_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Faculty Real-Time Events"])


# ---------------------------------------------------------------------------
# JWT authentication helper (mirrors the one in routers/websockets.py)
# ---------------------------------------------------------------------------

async def _authenticate_faculty_ws(token: str) -> dict | None:
    """
    Decode the JWT and return the user document if role is faculty/admin.
    Returns None on any failure (malformed token, wrong role, user not found).
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        email: str | None = payload.get("sub")
        if not email:
            return None

        user = await users_collection.find_one({"email": email})
        if user is None:
            return None

        if user.get("role") not in ("faculty", "admin"):
            return None

        return user
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Faculty WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/faculty/{session_id}")
async def faculty_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT bearer token for authentication"),
):
    """
    Persistent WebSocket connection for faculty analytics dashboards.

    The client should connect with:
        new WebSocket(`ws://localhost:8000/ws/faculty/<session_id>?token=<jwt>`)

    Events pushed to the client are JSON objects whose shape is governed by the
    `FacultyWSEvent` discriminated union (see services/websocket.py).
    """
    user = await _authenticate_faculty_ws(token)
    if user is None:
        logger.warning(
            "Faculty WS rejected — invalid token or insufficient role  session_id=%s",
            session_id,
        )
        await websocket.close(code=1008)  # Policy Violation — Unauthorized
        return

    faculty_id = str(user["_id"])
    logger.info(
        "Faculty WS handshake  faculty_id=%s  session_id=%s",
        faculty_id,
        session_id,
    )

    await faculty_manager.connect(websocket, session_id)

    try:
        while True:
            # Keep the connection alive; client can send heartbeat pings here.
            # We discard any incoming text — the channel is server→client only.
            await websocket.receive_text()
    except WebSocketDisconnect:
        faculty_manager.disconnect(session_id)
        logger.info(
            "Faculty WS closed gracefully  faculty_id=%s  session_id=%s",
            faculty_id,
            session_id,
        )
    except Exception as exc:
        faculty_manager.disconnect(session_id)
        logger.error(
            "Faculty WS error  faculty_id=%s  session_id=%s  error=%s",
            faculty_id,
            session_id,
            exc,
        )
