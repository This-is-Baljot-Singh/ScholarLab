# ScholarLab/backend/app/routers/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Dict, Any
from jose import jwt, JWTError
from app.database import settings, users_collection
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Real-Time Events"])

class ConnectionManager:
    def __init__(self):
        # Map user_id (string) to their active WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user: {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user: {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Push a real-time event to a specific student."""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                self.disconnect(user_id)

manager = ConnectionManager()

async def get_ws_user(token: str = Query(...)):
    """Authenticate WebSocket connections via query parameter."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        user = await users_collection.find_one({"email": email})
        return str(user["_id"]) if user else None
    except JWTError:
        return None

@router.websocket("/student")
async def student_websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user_id = await get_ws_user(token)
    if not user_id:
        await websocket.close(code=1008) # Policy Violation (Unauthorized)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive; can be used for client-side ping/pong later
            data = await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect(user_id)