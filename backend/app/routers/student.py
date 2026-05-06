# ScholarLab/backend/app/routers/student.py
from fastapi import APIRouter, Depends
from app.security import require_role
from app.schemas import RoleEnum
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Student Dashboard"])

@router.get("/dashboard")
async def get_student_dashboard(current_user: dict = Depends(require_role([RoleEnum.student]))):
    """
    Returns the initial state for the student dashboard.
    Will be populated with live MongoDB data in Sprint 3.
    """
    return {
        "activeSession": {
            "attendanceMarked": False,
            "lecture": {
                "id": "session_67890",
                "title": "Data Structures Lab",
                "startTime": datetime.now(timezone.utc).isoformat(),
                "location": "Engineering Hall 204",
                "classCode": "CS204"
            }
        },
        "unlockedCurriculum": [],
        "recentAttendance": [],
        "riskScore": 8
    }


# ---------------------------------------------------------------------------
# Endpoint: GET /api/student/curriculum/recent
# ---------------------------------------------------------------------------

class RecentUnlockedModule(BaseModel):
    """Recent curriculum module unlocked for a student."""
    id: str
    course_id: str
    title: str
    unlocked_at: str
    resource_uris: List[str] = Field(default_factory=list)


@router.get(
    "/curriculum/recent",
    response_model=List[RecentUnlockedModule],
    summary="Get recently unlocked curriculum modules for the current student",
)
async def get_recent_unlocked_curriculum(
    current_user: dict = Depends(require_role([RoleEnum.student])),
) -> List[RecentUnlockedModule]:
    """
    Retrieves the most recent curriculum modules unlocked for the current student.
    
    Returns modules in reverse chronological order (most recent first).
    This endpoint is called by the student dashboard to display unlocked materials.
    """
    from app.database import db
    from bson import ObjectId

    user_id = str(current_user["_id"])
    
    # Get student progress record
    student_progress_coll = db.get_collection("student_progress")
    progress_record = await student_progress_coll.find_one({"user_id": user_id})
    
    if not progress_record:
        # No progress yet
        return []
    
    unlocked_node_ids = progress_record.get("unlocked_node_ids", [])
    
    if not unlocked_node_ids:
        return []
    
    # Fetch curriculum nodes
    # Try both as ObjectId strings and as direct strings
    try:
        object_ids = [ObjectId(node_id) if len(node_id) == 24 else node_id for node_id in unlocked_node_ids]
    except:
        object_ids = unlocked_node_ids
    
    # Query curriculum collection for nodes (try multiple collection names)
    curriculum_coll = db.get_collection("curriculum_nodes")
    
    nodes = await curriculum_coll.find(
        {
            "$or": [
                {"_id": {"$in": object_ids}},
                {"node_id": {"$in": unlocked_node_ids}},
            ]
        }
    ).to_list(None)
    
    if not nodes:
        # Try the "curriculum" collection as fallback
        curriculum_coll = db.get_collection("curriculum")
        nodes = await curriculum_coll.find(
            {
                "$or": [
                    {"_id": {"$in": object_ids}},
                    {"node_id": {"$in": unlocked_node_ids}},
                ]
            }
        ).to_list(None)
    
    # Format response
    result = []
    for node in nodes:
        node_id = str(node.get("_id", ""))
        
        # Extract resources/URIs
        resource_uris = []
        if "resources" in node:
            for resource in node.get("resources", []):
                if isinstance(resource, dict) and "uri" in resource:
                    resource_uris.append(resource["uri"])
                elif isinstance(resource, str):
                    resource_uris.append(resource)
        
        result.append(
            RecentUnlockedModule(
                id=node_id,
                course_id=node.get("course_id", "general"),
                title=node.get("title", "Untitled Module"),
                unlocked_at=node.get("unlocked_at", datetime.now(timezone.utc).isoformat()),
                resource_uris=resource_uris,
            )
        )
    
    # Sort by unlocked_at descending (most recent first)
    result.sort(
        key=lambda x: x.unlocked_at,
        reverse=True
    )
    
    logger.info(
        "Retrieved %d recent unlocked modules for user=%s",
        len(result),
        user_id,
    )
    
    return result