# ScholarLab/backend/app/services/verification.py
from fastapi import HTTPException
from datetime import datetime, timezone
from app.database import attendance_collection
from app.utils.spatial import calculate_haversine
import logging

logger = logging.getLogger(__name__)

# Maximum allowed speed in meters per second (e.g., 30 m/s ≈ 108 km/h)
# This accommodates campus shuttle buses but easily catches GPS teleportation apps.
MAX_KINEMATIC_VELOCITY_MPS = 30.0 

async def verify_kinematic_velocity(user_id: str, current_lat: float, current_lon: float, current_time: datetime):
    """
    Prevents GPS teleportation by calculating the velocity required 
    to travel from the student's last logged location to the current one.
    """
    # Fetch the most recent verified attendance log for this user
    last_log = await attendance_collection.find_one(
        {"user_id": user_id, "status": "verified"},
        sort=[("timestamp", -1)]
    )

    if not last_log:
        return # First time logging in, no baseline exists to calculate velocity

    last_time = last_log["timestamp"]
    
    # Ensure timezone awareness
    if last_time.tzinfo is None:
        last_time = last_time.replace(tzinfo=timezone.utc)

    time_diff_seconds = (current_time - last_time).total_seconds()
    
    if time_diff_seconds <= 0:
        logger.warning(f"Time manipulation detected for user {user_id}")
        raise HTTPException(status_code=400, detail="Invalid chronological sequencing detected.")

    # Calculate great-circle distance between the two pings
    last_lat = last_log["coordinates"]["latitude"]
    last_lon = last_log["coordinates"]["longitude"]
    distance_meters = calculate_haversine(last_lat, last_lon, current_lat, current_lon)

    # Calculate required travel speed
    velocity_mps = distance_meters / time_diff_seconds

    if velocity_mps > MAX_KINEMATIC_VELOCITY_MPS:
        logger.warning(f"Kinematic Spoofing Alert! User {user_id} moved at {velocity_mps:.2f} m/s.")
        raise HTTPException(
            status_code=403, 
            detail=f"Kinematic anomaly detected. Required velocity of {velocity_mps:.1f} m/s exceeds physical transit limits."
        )

def verify_network_environment(provided_bssid: str, expected_bssids: list):
    """
    Cross-references the local Wi-Fi router MAC address (BSSID) 
    against the whitelisted campus access points for this specific geofence.
    """
    if not expected_bssids:
        return # No network constraints applied to this geofence
        
    if not provided_bssid or provided_bssid not in expected_bssids:
        logger.warning(f"Network mismatch: {provided_bssid} not in {expected_bssids}")
        raise HTTPException(
            status_code=403,
            detail="Network verification failed. Ensure your device is actively connected to the designated campus Wi-Fi infrastructure."
        )