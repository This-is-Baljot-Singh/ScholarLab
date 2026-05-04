# ScholarLab/backend/app/services/verification.py
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException
from app.utils.spatial import calculate_haversine
from app.database import attendance_collection

logger = logging.getLogger(__name__)

# Roughly 108 km/h, reasonable upper bound for local transit on or near campus
MAX_PLAUSIBLE_VELOCITY_MPS = 30.0 

async def verify_kinematic_velocity(
    user_id: str, 
    current_lat: float, 
    current_lng: float, 
    current_time: datetime
) -> None:
    """
    Calculates the velocity of the user since their last verified attendance.
    Raises a 403 HTTPException if the speed exceeds human/transit bounds, indicating GPS teleportation.
    """
    try:
        # Fetch the most recent verified attendance log
        last_log = await attendance_collection.find_one(
            {"user_id": user_id, "status": "verified"},
            sort=[("timestamp", -1)]
        )
        
        if not last_log:
            return  # First time logging in; no baseline to compare against

        last_time = last_log.get("timestamp")
        if not last_time:
            return

        # Ensure datetime is timezone-aware
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
            
        time_diff_seconds = (current_time - last_time).total_seconds()
        
        if time_diff_seconds < 60:
            return  # Ignore micro-fluctuations and signal bouncing within the same minute
            
        coordinates = last_log.get("coordinates", {})
        last_lat = coordinates.get("latitude")
        last_lng = coordinates.get("longitude")

        if last_lat is None or last_lng is None:
            return
        
        # Calculate great-circle distance
        distance_meters = calculate_haversine(last_lat, last_lng, current_lat, current_lng)
        
        # Calculate velocity in meters per second
        velocity = distance_meters / time_diff_seconds
        
        if velocity > MAX_PLAUSIBLE_VELOCITY_MPS:
            logger.warning(f"Kinematic anomaly detected for user {user_id}. Velocity: {velocity:.2f} m/s.")
            raise HTTPException(
                status_code=403, 
                detail=f"Kinematic anomaly detected. Velocity of {velocity:.2f} m/s exceeds human bounds."
            )
            
    except HTTPException:
        raise # Re-raise known security rejections
    except Exception as e:
        logger.error(f"Error executing kinematic velocity check for {user_id}: {str(e)}")
        # In a strict production environment, you might fail closed. 
        # Here we fail open on database read errors so valid users aren't locked out during a db hitch.
        pass

def verify_network_environment(bssid: Optional[str], expected_bssids: List[str]) -> bool:
    """
    Cross-references the device's provided Wi-Fi BSSID against the expected access points
    for the designated geofence. Adds an independent heuristic layer to GPS validation.
    Returns True if passed, False if failed (for moderate confidence flagging).
    """
    if not expected_bssids:
        return True  # No specific network signature required for this geofence

    if not bssid:
        logger.warning("Network verification failed: BSSID missing from payload.")
        return False

    # Normalize MAC addresses to uppercase and strip whitespace to prevent mismatch errors
    normalized_bssid = bssid.upper().strip()
    normalized_expected = [b.upper().strip() for b in expected_bssids]

    if normalized_bssid not in normalized_expected:
        logger.warning(f"Network spoofing attempt: BSSID {normalized_bssid} not in expected list {normalized_expected}.")
        return False

    return True