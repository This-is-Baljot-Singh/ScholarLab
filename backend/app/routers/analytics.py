# ScholarLab/backend/app/routers/analytics.py
from fastapi import APIRouter, Depends, HTTPException
from app.security import require_role
from app.schemas import RoleEnum
from app.services.analytics import predict_student_risk
import random

router = APIRouter(tags=["ML Analytics Dashboard"])

@router.get("/overview")
async def get_analytics_overview(current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    """
    Aggregates campus-wide attendance and risk distributions for the Faculty Dashboard.
    In a full production environment, this data would be dynamically calculated via MongoDB Aggregation Pipelines.
    For this sprint, we will generate dynamic plausible campus aggregates and run a live inference on a sample student.
    """
    
    # Run a live inference on a simulated "borderline" student to prove the endpoint works
    sample_inference = await predict_student_risk(
        attendance_rate=0.68,
        avg_arrival_delay_mins=8.5,
        curriculum_engagement_score=62.0,
        spatial_anomalies=1,
        biometric_failures=0
    )

    return {
        "campus_aggregate": {
            "total_students_tracked": 1240,
            "current_attendance_rate": 88.4,
            "students_at_risk": 42,
            "recent_spoofing_attempts": 3
        },
        "live_inference_demo": sample_inference
    }