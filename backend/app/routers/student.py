# ScholarLab/backend/app/routers/student.py
from fastapi import APIRouter, Depends
from app.security import require_role
from app.schemas import RoleEnum
from typing import Dict, Any

router = APIRouter(tags=["Student Dashboard"])

@router.get("/dashboard")
async def get_student_dashboard(current_user: dict = Depends(require_role([RoleEnum.student]))):
    """
    Returns the initial state for the student dashboard.
    Will be populated with live MongoDB data in Sprint 3.
    """
    return {
        "activeSession": None, # Set to None for now. The UI handles this gracefully.
        "unlockedCurriculum": [],
        "recentAttendance": []
    }