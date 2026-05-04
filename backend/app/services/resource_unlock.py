"""
Resource Unlock Service: Progressive resource unlocking based on attendance.

Pipeline:
1. Get verified curriculum mappings for session
2. Query attendance decisions: A_t = True?
3. For each student with A_t = True, unlock associated resources
4. Track unlock events (audit trail)
5. Progressive unlock: resources unlocked only after verification

Resource Types:
- lecture_notes: PDF, markdown notes
- slides: Presentation slides
- recordings: Session recording
- supplementary: Additional materials
- assignments: Homework/exercises
- solutions: Answer keys (optional)

Gate: A_t = True (from attendance verification pipeline)
      → resource_unlocked = True
"""

import logging
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class ResourceType(str, Enum):
    """Types of curriculum resources."""
    LECTURE_NOTES = "lecture_notes"
    SLIDES = "slides"
    RECORDINGS = "recordings"
    SUPPLEMENTARY = "supplementary"
    ASSIGNMENTS = "assignments"
    SOLUTIONS = "solutions"


class CurriculumResource(BaseModel):
    """Individual curriculum resource."""
    resource_id: str
    curriculum_node_id: str
    resource_type: ResourceType
    title: str
    description: Optional[str] = None
    uri: str  # URL or file path to resource (encrypted in DB)
    size_bytes: Optional[int] = None
    requires_attendance: bool = True  # Must have A_t = True to access?
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResourceAccess(BaseModel):
    """Record of student accessing resource."""
    access_id: str
    user_id: str
    resource_id: str
    session_id: str
    curriculum_node_id: str
    resource_type: ResourceType
    # Access unlock
    attendance_verified: bool  # Was A_t = True?
    attendance_decision_id: Optional[str] = None
    # Access record
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    bytes_transferred: Optional[int] = None


class ProgressiveUnlock(BaseModel):
    """Progressive unlock event."""
    unlock_id: str
    user_id: str
    session_id: str
    course_id: str
    # Unlock trigger
    attendance_verified: bool  # A_t = True
    attendance_decision_id: str
    # Resources unlocked
    resource_ids: List[str]
    curriculum_node_ids: Set[str]
    # Metadata
    unlocked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    unlock_count: int  # How many resources unlocked?


# ============================================================================
# RESOURCE UNLOCK SERVICE
# ============================================================================

class ResourceUnlockService:
    """
    Manages progressive resource unlocking based on attendance.
    
    Workflow:
    1. Student checks into session (attendance verification pipeline)
    2. A_t = True → attendance_verified = True
    3. Query verified curriculum mappings for session
    4. Find all resources for matched nodes
    5. Unlock resources → resource_uri returned to student
    6. Log access (audit trail)
    
    Privacy: Resources encrypted in transit. Only students with A_t = True
    can decrypt/access.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.resources_col: AsyncIOMotorCollection = db["curriculum_resources"]
        self.accesses_col: AsyncIOMotorCollection = db["curriculum_resource_accesses"]
        self.unlocks_col: AsyncIOMotorCollection = db["curriculum_progressive_unlocks"]
    
    async def initialize(self):
        """Setup collection indexes."""
        await self.resources_col.create_index("curriculum_node_id")
        await self.resources_col.create_index("resource_type")
        await self.resources_col.create_index("requires_attendance")
        
        await self.accesses_col.create_index("user_id")
        await self.accesses_col.create_index("resource_id")
        await self.accesses_col.create_index("session_id")
        await self.accesses_col.create_index("accessed_at")
        await self.accesses_col.create_index(
            "accessed_at",
            expireAfterSeconds=7776000  # 90 days
        )
        
        await self.unlocks_col.create_index("user_id")
        await self.unlocks_col.create_index("session_id")
        await self.unlocks_col.create_index("unlocked_at")
        
        logger.info("Resource unlock service initialized")
    
    # ========================================================================
    # RESOURCE REGISTRATION
    # ========================================================================
    
    async def register_resource(
        self,
        curriculum_node_id: str,
        resource_type: ResourceType,
        title: str,
        uri: str,
        description: Optional[str] = None,
        requires_attendance: bool = True,
    ) -> CurriculumResource:
        """
        Register a curriculum resource.
        
        Args:
            curriculum_node_id: Associated syllabus node
            resource_type: Type of resource
            title: Resource title
            uri: URL/path to resource
            description: Optional description
            requires_attendance: Only unlock if A_t = True?
        
        Returns:
            CurriculumResource
        """
        resource_id = str(ObjectId())
        
        resource = CurriculumResource(
            resource_id=resource_id,
            curriculum_node_id=curriculum_node_id,
            resource_type=resource_type,
            title=title,
            description=description,
            uri=uri,
            requires_attendance=requires_attendance,
        )
        
        doc = resource.dict()
        doc["_id"] = ObjectId()
        await self.resources_col.insert_one(doc)
        
        logger.info(
            f"Resource registered: {title} ({resource_type})",
            extra={"curriculum_node_id": curriculum_node_id}
        )
        
        return resource
    
    # ========================================================================
    # PROGRESSIVE UNLOCK (ATTENDANCE-GATED)
    # ========================================================================
    
    async def unlock_resources_for_student(
        self,
        user_id: str,
        session_id: str,
        course_id: str,
        attendance_verified: bool,  # A_t
        attendance_decision_id: str,
        curriculum_node_ids: List[str],  # Nodes from verified mappings
    ) -> ProgressiveUnlock:
        """
        Progressively unlock resources for student based on attendance.
        
        Gate: attendance_verified == True (A_t = True)
        
        If attendance_verified = True:
          - Query resources for all curriculum_node_ids
          - Unlock and return URIs
          - Log access
        Else:
          - No resources unlocked
          - Log attempted access (failed gate)
        
        Args:
            user_id: Student ID
            session_id: Lecture session ID
            course_id: Course ID
            attendance_verified: A_t from attendance verification
            attendance_decision_id: ID of attendance decision
            curriculum_node_ids: Curriculum nodes with verified mappings
        
        Returns:
            ProgressiveUnlock with unlocked resource IDs
        """
        unlock_id = str(ObjectId())
        unlocked_resources = []
        unlocked_nodes = set()
        
        if not attendance_verified:
            # Attendance gate failed: no resources unlocked
            logger.info(
                f"Attendance gate failed for {user_id} in {session_id}: A_t = False",
                extra={"user_id": user_id, "session_id": session_id}
            )
            
            unlock = ProgressiveUnlock(
                unlock_id=unlock_id,
                user_id=user_id,
                session_id=session_id,
                course_id=course_id,
                attendance_verified=False,
                attendance_decision_id=attendance_decision_id,
                resource_ids=[],
                curriculum_node_ids=set(),
                unlock_count=0,
            )
            
            # Log attempted unlock
            await self.unlocks_col.insert_one(unlock.dict(exclude={"curriculum_node_ids"}))
            
            return unlock
        
        # ===== Attendance gate PASSED (A_t = True) =====
        
        # Query all resources for these curriculum nodes
        resources = await self._get_resources_for_nodes(curriculum_node_ids)
        
        for resource in resources:
            unlocked_resources.append(resource.resource_id)
            unlocked_nodes.add(resource.curriculum_node_id)
            
            # Log access
            await self._log_resource_access(
                user_id=user_id,
                resource_id=resource.resource_id,
                resource_type=resource.resource_type,
                session_id=session_id,
                curriculum_node_id=resource.curriculum_node_id,
                attendance_verified=True,
                attendance_decision_id=attendance_decision_id,
            )
        
        # Create unlock record
        unlock = ProgressiveUnlock(
            unlock_id=unlock_id,
            user_id=user_id,
            session_id=session_id,
            course_id=course_id,
            attendance_verified=True,
            attendance_decision_id=attendance_decision_id,
            resource_ids=unlocked_resources,
            curriculum_node_ids=unlocked_nodes,
            unlock_count=len(unlocked_resources),
        )
        
        # Store unlock event
        doc = unlock.dict(exclude={"curriculum_node_ids"})
        doc["_id"] = ObjectId()
        doc["curriculum_node_ids_list"] = list(unlocked_nodes)
        await self.unlocks_col.insert_one(doc)
        
        logger.info(
            f"Progressively unlocked {len(unlocked_resources)} resources for {user_id}",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "resource_count": len(unlocked_resources),
                "attendance_verified": True,
            }
        )
        
        return unlock
    
    # ========================================================================
    # RESOURCE QUERYING
    # ========================================================================
    
    async def _get_resources_for_nodes(
        self,
        curriculum_node_ids: List[str],
    ) -> List[CurriculumResource]:
        """Query all resources for given curriculum nodes."""
        if not curriculum_node_ids:
            return []
        
        cursor = self.resources_col.find({
            "curriculum_node_id": {"$in": curriculum_node_ids},
            "requires_attendance": True,
        })
        
        resources_raw = await cursor.to_list(length=1000)
        
        return [CurriculumResource(**doc) for doc in resources_raw]
    
    async def get_resource_by_id(self, resource_id: str) -> Optional[CurriculumResource]:
        """Retrieve resource by ID."""
        doc = await self.resources_col.find_one({"resource_id": resource_id})
        if doc:
            doc.pop("_id", None)
            return CurriculumResource(**doc)
        return None
    
    # ========================================================================
    # ACCESS LOGGING
    # ========================================================================
    
    async def _log_resource_access(
        self,
        user_id: str,
        resource_id: str,
        resource_type: ResourceType,
        session_id: str,
        curriculum_node_id: str,
        attendance_verified: bool,
        attendance_decision_id: str,
        ip_address: Optional[str] = None,
    ) -> ResourceAccess:
        """Log resource access event."""
        access_id = str(ObjectId())
        
        access = ResourceAccess(
            access_id=access_id,
            user_id=user_id,
            resource_id=resource_id,
            session_id=session_id,
            curriculum_node_id=curriculum_node_id,
            resource_type=resource_type,
            attendance_verified=attendance_verified,
            attendance_decision_id=attendance_decision_id,
            ip_address=ip_address,
        )
        
        doc = access.dict()
        doc["_id"] = ObjectId()
        await self.accesses_col.insert_one(doc)
        
        return access
    
    async def record_resource_download(
        self,
        access_id: str,
        bytes_transferred: int,
    ):
        """Record bytes transferred for resource access."""
        await self.accesses_col.update_one(
            {"access_id": access_id},
            {"$set": {"bytes_transferred": bytes_transferred}},
        )
    
    # ========================================================================
    # ACCESS AUDIT TRAIL
    # ========================================================================
    
    async def get_student_resource_accesses(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> List[ResourceAccess]:
        """Get all resource accesses for a student."""
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        
        cursor = self.accesses_col.find(query).sort("accessed_at", -1)
        accesses_raw = await cursor.to_list(length=1000)
        
        return [ResourceAccess(**doc) for doc in accesses_raw]
    
    async def get_session_unlock_statistics(self, session_id: str) -> Dict:
        """Get resource unlock statistics for session."""
        cursor = self.unlocks_col.aggregate([
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": "$session_id",
                    "total_students": {"$sum": 1},
                    "attendance_verified_count": {
                        "$sum": {"$cond": ["$attendance_verified", 1, 0]}
                    },
                    "total_resources_unlocked": {"$sum": "$unlock_count"},
                    "avg_resources_per_student": {"$avg": "$unlock_count"},
                }
            },
        ])
        
        result = await cursor.to_list(length=1)
        return result[0] if result else {}
    
    # ========================================================================
    # AUDIT & ANALYTICS
    # ========================================================================
    
    async def get_most_accessed_resources(
        self,
        session_id: str,
        top_k: int = 10,
    ) -> List[Dict]:
        """Get most accessed resources in a session."""
        cursor = self.accesses_col.aggregate([
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": "$resource_id",
                    "access_count": {"$sum": 1},
                    "total_bytes": {"$sum": {"$ifNull": ["$bytes_transferred", 0]}},
                }
            },
            {"$sort": {"access_count": -1}},
            {"$limit": top_k},
        ])
        
        return await cursor.to_list(length=top_k)
    
    async def get_attendance_unlock_rate(self, session_id: str) -> Dict:
        """Calculate attendance-gated unlock rate."""
        total = await self.unlocks_col.count_documents({"session_id": session_id})
        verified = await self.unlocks_col.count_documents({
            "session_id": session_id,
            "attendance_verified": True,
        })
        
        rate = (verified / total) if total > 0 else 0.0
        
        return {
            "session_id": session_id,
            "total_unlock_events": total,
            "attendance_verified_unlocks": verified,
            "unlock_rate": rate,
        }
