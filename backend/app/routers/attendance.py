# ScholarLab/backend/app/routers/attendance.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.database import attendance_collection, geofences_collection, users_collection, settings
from app.security import require_role
from app.schemas import RoleEnum
from app.utils.spatial import calculate_haversine, ray_casting_polygon
from app.services.verification import verify_kinematic_velocity, verify_network_environment
from bson import ObjectId
import logging
from app.services.curriculum_engine import process_curriculum_unlocks
from app.routers.websockets import manager

# WebAuthn Imports
from webauthn import verify_authentication_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/attendance", tags=["Attendance Verification Pipeline"])

# --- WebAuthn Environment (Ensure these match your frontend deployment) ---
RP_ID = "localhost" 
ORIGIN = "http://localhost:5173"

class AttendancePayload(BaseModel):
    session_id: str
    geofence_id: str
    latitude: float
    longitude: float
    bssid: Optional[str] = None
    cryptographic_signature: Dict[str, Any] # Now accepts the raw JSON object from @simplewebauthn/browser

@router.post("/verify")
async def verify_and_log_attendance(payload: AttendancePayload, request: Request, current_user: dict = Depends(require_role([RoleEnum.student]))):
    current_time = datetime.now(timezone.utc)
    user_id = str(current_user["_id"])
    
    # ==========================================
    # PHASE 1: BIOMETRIC CRYPTOGRAPHIC PROOF
    # ==========================================
    user = await users_collection.find_one({"_id": current_user["_id"]})
    if not user or "current_challenge" not in user:
        raise HTTPException(status_code=400, detail="Biometric challenge missing or expired. Please restart the flow.")

    credential_id = payload.cryptographic_signature.get("id")
    stored_credential = next((c for c in user.get("webauthn_credentials", []) if c["credential_id"] == credential_id), None)

    if not stored_credential:
        raise HTTPException(status_code=403, detail="Unrecognized biometric device. Please register this device first.")

    try:
        verification = verify_authentication_response(
            credential=payload.cryptographic_signature,
            expected_challenge=user["current_challenge"],
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=stored_credential["public_key"],
            credential_current_sign_count=stored_credential["sign_count"]
        )

        # Replay Attack Protection: Update sign count and clear challenge
        await users_collection.update_one(
            {"_id": user["_id"], "webauthn_credentials.credential_id": credential_id},
            {
                "$set": {"webauthn_credentials.$.sign_count": verification.new_sign_count},
                "$unset": {"current_challenge": ""}
            }
        )
    except Exception as e:
        logger.error(f"Spoofing attempt detected. WebAuthn Error: {str(e)}")
        raise HTTPException(status_code=403, detail="Biometric verification failed. Integrity compromised.")

    # ==========================================
    # PHASE 2: SPATIAL GEOFENCE VALIDATION
    # ==========================================
    try:
        geofence = await geofences_collection.find_one({"_id": ObjectId(payload.geofence_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid Geofence ID format")
        
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence bounds not found")

    is_within_bounds = False
    user_point = (payload.longitude, payload.latitude) # GeoJSON format: [lon, lat]

    # Calculate distance based on Geofence Type
    if geofence["type"] == "radial":
        center_lon, center_lat = geofence["boundary"]["coordinates"]
        distance = calculate_haversine(center_lat, center_lon, payload.latitude, payload.longitude)
        if distance <= geofence.get("radius", 50.0):
            is_within_bounds = True
    elif geofence["type"] == "polygon":
        polygon_coords = geofence["boundary"]["coordinates"][0]
        is_within_bounds = ray_casting_polygon(user_point, polygon_coords)

    if not is_within_bounds:
        raise HTTPException(status_code=403, detail="Spatial rejection: You are currently outside the designated lecture boundary.")

    # ==========================================
    # PHASE 3: CONTEXTUAL HEURISTICS (Velocity & Network)
    # ==========================================
    verify_network_environment(payload.bssid, geofence.get("expected_bssids", []))
    await verify_kinematic_velocity(user_id, payload.latitude, payload.longitude, current_time)

    # ==========================================
    # PHASE 4: IMMUTABLE LOG CREATION
    # ==========================================
    log_entry = {
        "user_id": user_id,
        "session_id": payload.session_id,
        "geofence_id": payload.geofence_id,
        "timestamp": current_time,
        "coordinates": {"latitude": payload.latitude, "longitude": payload.longitude},
        "network": {"bssid": payload.bssid, "ip_address": request.client.host},
        "status": "verified"
    }

    result = await attendance_collection.insert_one(log_entry)
    
    # ==========================================
    # PHASE 5: EVENT-DRIVEN CURRICULUM SYNC
    # ==========================================
    try:
        # Traverse Knowledge Graph
        unlocked_items = await process_curriculum_unlocks(user_id, payload.session_id)
        
        # Push each unlocked item to the user's active WebSocket session
        for item in unlocked_items:
            ws_payload = {
                "type": "curriculum:unlocked",
                "payload": {
                    "message": "Cryptography Verified. Material Unlocked.",
                    "curriculumItem": item
                }
            }
            # This directly targets ONLY the student who marked attendance
            await manager.send_personal_message(ws_payload, user_id)
            
    except Exception as e:
        logger.error(f"Curriculum Sync Failed for {user_id}: {str(e)}")
        # We don't raise an HTTPException here because the attendance itself was successful.
        # We fail gracefully on the sync side.

    return {"message": "Presence verified cryptographically.", "log_id": str(result.inserted_id)}