# ScholarLab/backend/app/routers/students.py
from fastapi import APIRouter, Depends, HTTPException
from app.security import require_role
from app.schemas import RoleEnum
from app.database import users_collection, attendance_collection, sessions_collection
from bson import ObjectId
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Student Management (Faculty View)"])

@router.get("/{student_id}")
async def get_student_profile(student_id: str, current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    """
    Returns detailed profile for a specific student, including personal details
    and full attendance history with zero-trust gate results.
    """
    try:
        # 1. Fetch Student Personal Details
        # Try finding by ObjectId or Email
        student = await users_collection.find_one({
            "$or": [
                {"_id": ObjectId(student_id) if len(student_id) == 24 else None},
                {"email": student_id}
            ]
        })
        
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # 2. Fetch Attendance History
        attendance_cursor = attendance_collection.find({"user_id": str(student["_id"])}).sort("timestamp", -1)
        attendance_history = await attendance_cursor.to_list(length=100)
        
        # 3. Enrich Attendance with Session Titles
        enriched_history = []
        for record in attendance_history:
            session = await sessions_collection.find_one({"id": record["session_id"]})
            session_title = session.get("title", session.get("lectureId", "Live Session")) if session else "Live Session"
            
            enriched_history.append({
                "id": str(record["_id"]),
                "sessionId": record["session_id"],
                "sessionTitle": session_title,
                "timestamp": record["timestamp"].isoformat() if hasattr(record["timestamp"], "isoformat") else str(record["timestamp"]),
                "status": record["status"],
                "gates": record.get("gates", {
                    "device": True,
                    "kinematic": True,
                    "memory": True,
                    "network": True,
                    "biometric": True,
                    "geofence": True
                })
            })

        return {
            "personal_details": {
                "id": str(student["_id"]),
                "name": student["full_name"],
                "email": student["email"],
                "roll_number": student.get("roll_number", "N/A"),
                "address": student.get("address", "N/A"),
                "parents_contact": student.get("parents_contact", "N/A"),
            },
            "attendance_history": enriched_history
        }
    except Exception as e:
        logger.error(f"Error fetching student profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load student profile: {str(e)}")
