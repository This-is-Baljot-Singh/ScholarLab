"""
Verification Agent: Manual review workflow for below-threshold mappings.

Pipeline:
1. Flag mappings below confidence threshold δ
2. Create verification tasks for faculty
3. Faculty reviews and approves/rejects/corrects mappings
4. Store verified mappings
5. Unlock resources for students

Verification Status:
- pending: Waiting for faculty review
- approved: Faculty confirmed the mapping
- rejected: Mapping was incorrect
- corrected: Faculty provided correct mapping
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

from app.services.syllabus_matcher import SyllabusNodeMatch

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class VerificationStatus(str, Enum):
    """Verification workflow status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class VerificationTask(BaseModel):
    """Manual verification task for faculty."""
    task_id: str
    session_id: str
    course_id: str
    topic: str
    topic_confidence: float
    # Original mapping (from agent)
    original_node_id: str
    original_node_title: str
    similarity_score: float
    # Verification
    status: VerificationStatus = VerificationStatus.PENDING
    faculty_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None
    # Faculty decision (if corrected)
    corrected_node_id: Optional[str] = None
    corrected_node_title: Optional[str] = None


class VerificationResult(BaseModel):
    """Result of verification workflow."""
    task_id: str
    session_id: str
    original_mapping: SyllabusNodeMatch
    verification_status: VerificationStatus
    faculty_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    # If corrected
    corrected_mapping: Optional[SyllabusNodeMatch] = None
    notes: Optional[str] = None


class BulkVerificationStatus(BaseModel):
    """Status of bulk verification for a session."""
    session_id: str
    course_id: str
    total_below_threshold: int
    pending: int
    approved: int
    rejected: int
    corrected: int
    completion_rate: float = Field(ge=0.0, le=1.0)


# ============================================================================
# VERIFICATION AGENT
# ============================================================================

class VerificationAgent:
    """
    Manages manual verification workflow for low-confidence mappings.
    
    Workflow:
    1. Identify mappings below threshold δ
    2. Create verification tasks
    3. Notify faculty
    4. Track faculty decisions
    5. Store verified mappings
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.tasks_col: AsyncIOMotorCollection = db["curriculum_verification_tasks"]
        self.verified_mappings_col: AsyncIOMotorCollection = db["curriculum_verified_mappings"]
    
    async def initialize(self):
        """Setup collection indexes."""
        await self.tasks_col.create_index("task_id", unique=True)
        await self.tasks_col.create_index("session_id")
        await self.tasks_col.create_index("course_id")
        await self.tasks_col.create_index("status")
        await self.tasks_col.create_index("faculty_id")
        await self.tasks_col.create_index("created_at")
        
        await self.verified_mappings_col.create_index("session_id")
        await self.verified_mappings_col.create_index("course_id")
        await self.verified_mappings_col.create_index("task_id")
        
        logger.info("Verification agent initialized")
    
    # ========================================================================
    # TASK CREATION
    # ========================================================================
    
    async def create_verification_tasks(
        self,
        session_id: str,
        course_id: str,
        below_threshold_matches: List[SyllabusNodeMatch],
    ) -> List[VerificationTask]:
        """
        Create verification tasks for all below-threshold mappings.
        
        Args:
            session_id: Lecture session ID
            course_id: Course ID
            below_threshold_matches: Mappings below δ (confidence threshold)
        
        Returns:
            List of created VerificationTask objects
        """
        tasks = []
        
        for match in below_threshold_matches:
            task_id = self._generate_task_id()
            
            task = VerificationTask(
                task_id=task_id,
                session_id=session_id,
                course_id=course_id,
                topic=match.topic,
                topic_confidence=match.topic_confidence,
                original_node_id=match.curriculum_node_id,
                original_node_title=match.node_title,
                similarity_score=match.similarity_score,
                status=VerificationStatus.PENDING,
            )
            
            # Store in DB
            doc = task.dict()
            doc["_id"] = ObjectId()
            doc["created_at"] = datetime.now(timezone.utc)
            await self.tasks_col.insert_one(doc)
            
            tasks.append(task)
        
        logger.info(
            f"Created {len(tasks)} verification tasks for {session_id}",
            extra={
                "session_id": session_id,
                "course_id": course_id,
                "task_count": len(tasks),
            }
        )
        
        return tasks
    
    @staticmethod
    def _generate_task_id() -> str:
        """Generate unique task ID."""
        return str(ObjectId())
    
    # ========================================================================
    # TASK RETRIEVAL
    # ========================================================================
    
    async def get_pending_tasks(
        self,
        course_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
    ) -> List[VerificationTask]:
        """
        Get pending verification tasks.
        
        Args:
            course_id: Filter by course (optional)
            faculty_id: Filter by faculty (optional)
        
        Returns:
            List of pending tasks
        """
        query = {"status": VerificationStatus.PENDING}
        
        if course_id:
            query["course_id"] = course_id
        if faculty_id:
            query["faculty_id"] = faculty_id
        
        cursor = self.tasks_col.find(query).sort("created_at", 1)
        tasks_raw = await cursor.to_list(length=1000)
        
        return [VerificationTask(**doc) for doc in tasks_raw]
    
    async def get_task(self, task_id: str) -> Optional[VerificationTask]:
        """Retrieve single task."""
        doc = await self.tasks_col.find_one({"task_id": task_id})
        if doc:
            doc.pop("_id", None)
            return VerificationTask(**doc)
        return None
    
    # ========================================================================
    # TASK VERIFICATION (FACULTY ACTION)
    # ========================================================================
    
    async def approve_mapping(
        self,
        task_id: str,
        faculty_id: str,
        notes: Optional[str] = None,
    ) -> VerificationResult:
        """
        Faculty approves the suggested mapping.
        
        Args:
            task_id: Task ID
            faculty_id: Faculty performing verification
            notes: Optional notes
        
        Returns:
            VerificationResult
        """
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Update task status
        await self.tasks_col.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": VerificationStatus.APPROVED,
                    "faculty_id": faculty_id,
                    "verified_at": datetime.now(timezone.utc),
                    "notes": notes,
                }
            }
        )
        
        # Store verified mapping
        original_match = SyllabusNodeMatch(
            topic=task.topic,
            topic_confidence=task.topic_confidence,
            curriculum_node_id=task.original_node_id,
            node_title=task.original_node_title,
            similarity_score=task.similarity_score,
            rank=1,
        )
        
        result = VerificationResult(
            task_id=task_id,
            session_id=task.session_id,
            original_mapping=original_match,
            verification_status=VerificationStatus.APPROVED,
            faculty_id=faculty_id,
            verified_at=datetime.now(timezone.utc),
            notes=notes,
        )
        
        await self._store_verified_mapping(result)
        
        logger.info(
            f"Task approved: {task_id}",
            extra={"faculty_id": faculty_id}
        )
        
        return result
    
    async def reject_mapping(
        self,
        task_id: str,
        faculty_id: str,
        notes: Optional[str] = None,
    ) -> VerificationResult:
        """
        Faculty rejects the suggested mapping (wrong or low quality).
        
        Args:
            task_id: Task ID
            faculty_id: Faculty performing verification
            notes: Reason for rejection
        
        Returns:
            VerificationResult
        """
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Update task status
        await self.tasks_col.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": VerificationStatus.REJECTED,
                    "faculty_id": faculty_id,
                    "verified_at": datetime.now(timezone.utc),
                    "notes": notes,
                }
            }
        )
        
        # Store rejection
        original_match = SyllabusNodeMatch(
            topic=task.topic,
            topic_confidence=task.topic_confidence,
            curriculum_node_id=task.original_node_id,
            node_title=task.original_node_title,
            similarity_score=task.similarity_score,
            rank=1,
        )
        
        result = VerificationResult(
            task_id=task_id,
            session_id=task.session_id,
            original_mapping=original_match,
            verification_status=VerificationStatus.REJECTED,
            faculty_id=faculty_id,
            verified_at=datetime.now(timezone.utc),
            notes=notes,
        )
        
        logger.info(
            f"Task rejected: {task_id}",
            extra={"faculty_id": faculty_id, "reason": notes}
        )
        
        return result
    
    async def correct_mapping(
        self,
        task_id: str,
        correct_node_id: str,
        correct_node_title: str,
        faculty_id: str,
        notes: Optional[str] = None,
    ) -> VerificationResult:
        """
        Faculty corrects the suggested mapping (provides right answer).
        
        Args:
            task_id: Task ID
            correct_node_id: Correct curriculum node ID
            correct_node_title: Correct node title
            faculty_id: Faculty performing verification
            notes: Correction notes
        
        Returns:
            VerificationResult
        """
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Update task status
        await self.tasks_col.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": VerificationStatus.CORRECTED,
                    "corrected_node_id": correct_node_id,
                    "corrected_node_title": correct_node_title,
                    "faculty_id": faculty_id,
                    "verified_at": datetime.now(timezone.utc),
                    "notes": notes,
                }
            }
        )
        
        # Store corrected mapping
        original_match = SyllabusNodeMatch(
            topic=task.topic,
            topic_confidence=task.topic_confidence,
            curriculum_node_id=task.original_node_id,
            node_title=task.original_node_title,
            similarity_score=task.similarity_score,
            rank=1,
        )
        
        corrected_match = SyllabusNodeMatch(
            topic=task.topic,
            topic_confidence=task.topic_confidence,
            curriculum_node_id=correct_node_id,
            node_title=correct_node_title,
            similarity_score=1.0,  # Faculty confirmed, perfect match
            rank=1,
        )
        
        result = VerificationResult(
            task_id=task_id,
            session_id=task.session_id,
            original_mapping=original_match,
            corrected_mapping=corrected_match,
            verification_status=VerificationStatus.CORRECTED,
            faculty_id=faculty_id,
            verified_at=datetime.now(timezone.utc),
            notes=notes,
        )
        
        await self._store_verified_mapping(result)
        
        logger.info(
            f"Task corrected: {task_id}",
            extra={
                "faculty_id": faculty_id,
                "original_node": task.original_node_id,
                "corrected_node": correct_node_id,
            }
        )
        
        return result
    
    # ========================================================================
    # STORAGE & RETRIEVAL
    # ========================================================================
    
    async def _store_verified_mapping(self, result: VerificationResult):
        """Store verified mapping result."""
        doc = result.dict()
        doc["_id"] = ObjectId()
        doc["stored_at"] = datetime.now(timezone.utc)
        await self.verified_mappings_col.insert_one(doc)
    
    async def get_verified_mappings_for_session(
        self,
        session_id: str,
    ) -> List[VerificationResult]:
        """Get all verified mappings for a session."""
        cursor = self.verified_mappings_col.find({"session_id": session_id})
        results_raw = await cursor.to_list(length=1000)
        
        return [VerificationResult(**doc) for doc in results_raw]
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_session_verification_status(
        self,
        session_id: str,
    ) -> BulkVerificationStatus:
        """Get verification status for a session."""
        cursor = self.tasks_col.aggregate([
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": "$session_id",
                    "total": {"$sum": 1},
                    "pending": {"$sum": {"$cond": [{"$eq": ["$status", VerificationStatus.PENDING]}, 1, 0]}},
                    "approved": {"$sum": {"$cond": [{"$eq": ["$status", VerificationStatus.APPROVED]}, 1, 0]}},
                    "rejected": {"$sum": {"$cond": [{"$eq": ["$status", VerificationStatus.REJECTED]}, 1, 0]}},
                    "corrected": {"$sum": {"$cond": [{"$eq": ["$status", VerificationStatus.CORRECTED]}, 1, 0]}},
                }
            },
        ])
        
        result = await cursor.to_list(length=1)
        if not result:
            return BulkVerificationStatus(
                session_id=session_id,
                course_id="",
                total_below_threshold=0,
                pending=0,
                approved=0,
                rejected=0,
                corrected=0,
                completion_rate=0.0,
            )
        
        data = result[0]
        total = data.get("total", 0)
        completion_rate = 1.0 - (data.get("pending", 0) / total) if total > 0 else 0.0
        
        return BulkVerificationStatus(
            session_id=session_id,
            course_id="",  # Would need to query separately
            total_below_threshold=total,
            pending=data.get("pending", 0),
            approved=data.get("approved", 0),
            rejected=data.get("rejected", 0),
            corrected=data.get("corrected", 0),
            completion_rate=completion_rate,
        )
    
    async def get_faculty_workload(self, faculty_id: str) -> Dict:
        """Get verification task statistics for a faculty member."""
        cursor = self.tasks_col.aggregate([
            {"$match": {"faculty_id": faculty_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                }
            },
        ])
        
        stats = await cursor.to_list(length=10)
        
        return {
            "faculty_id": faculty_id,
            "total_verified": sum(s["count"] for s in stats),
            "by_status": {s["_id"]: s["count"] for s in stats},
        }
