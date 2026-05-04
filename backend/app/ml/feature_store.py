"""
Feature Store: Extract rolling features for risk prediction model.

Computes student-session features from attendance, curriculum, and engagement data:
- Cumulative attendance rate (a_t)
- Late-arrival frequency (delta_a_t)
- Curriculum coverage gaps (c_t)
- Temporal trends (delta_a_t, attendance volatility)
- Engagement signals (biometric success rate, resource access)

Features are stored in feature_store collection for training/inference.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class StudentFeatures(BaseModel):
    """Computed features for a single student at time t."""
    student_id: str
    course_id: str
    session_id: str
    # Attendance features
    cumulative_attendance_rate: float = Field(ge=0.0, le=1.0)  # a_t
    late_arrival_count: int  # N_late
    late_arrival_frequency: float = Field(ge=0.0, le=1.0)  # f_late = N_late / total_sessions
    attendance_change: float = Field(ge=-1.0, le=1.0)  # delta_a_t (change from previous)
    attendance_volatility: float = Field(ge=0.0, le=1.0)  # Std dev of attendance (on-time=1, late=0.5, absent=0)
    # Curriculum features
    curriculum_coverage: float = Field(ge=0.0, le=1.0)  # c_t (topics mastered / total topics)
    curriculum_coverage_trend: float = Field(ge=-1.0, le=1.0)  # Change in c_t
    topics_behind: int  # Number of topics student hasn't accessed
    # Engagement features
    resource_access_count: int  # Total resources downloaded
    biometric_success_rate: float = Field(ge=0.0, le=1.0)  # Fraction of A_t=True (attendance decisions)
    # Temporal context
    days_since_start: int  # Days into course
    weeks_into_semester: int  # Week number
    is_late_in_semester: bool  # > 80% through course
    # Computed at
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureExtractionResult(BaseModel):
    """Result of feature extraction for a cohort/course."""
    course_id: str
    session_id: str
    extraction_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    student_features: List[StudentFeatures]
    feature_count: int  # Total students with features
    missing_students: int  # Students with incomplete data


class CourseMetadata(BaseModel):
    """Course metadata for feature computation."""
    course_id: str
    course_name: str
    total_sessions: int
    total_curriculum_topics: int
    start_date: datetime
    end_date: datetime


# ============================================================================
# FEATURE STORE EXTRACTOR
# ============================================================================

class FeatureStoreExtractor:
    """
    Extracts and computes features for risk prediction model.
    
    Runs after every attendance session.
    
    Features extracted:
    - Attendance: a_t (cumulative rate), delta_a_t (change), f_late (late frequency)
    - Curriculum: c_t (coverage), topics_behind (gaps)
    - Engagement: resource_access_count, biometric_success_rate
    - Temporal: days_since_start, weeks_into_semester, is_late_in_semester
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.feature_store_col: AsyncIOMotorCollection = db["feature_store"]
        self.attendance_events_col: AsyncIOMotorCollection = db["attendance_events"]
        self.curriculum_events_col: AsyncIOMotorCollection = db["curriculum_events"]
        self.resource_accesses_col: AsyncIOMotorCollection = db["curriculum_resource_accesses"]
        self.courses_col: AsyncIOMotorCollection = db["courses"]
        self.users_col: AsyncIOMotorCollection = db["users"]
    
    async def initialize(self):
        """Setup collection indexes."""
        await self.feature_store_col.create_index("student_id")
        await self.feature_store_col.create_index("course_id")
        await self.feature_store_col.create_index("session_id")
        await self.feature_store_col.create_index([("student_id", 1), ("course_id", 1), ("session_id", 1)], unique=True)
        await self.feature_store_col.create_index("computed_at")
        logger.info("Feature store initialized")
    
    # ========================================================================
    # ATTENDANCE FEATURES
    # ========================================================================
    
    async def _compute_attendance_features(
        self,
        student_id: str,
        course_id: str,
        session_id: str,
    ) -> Tuple[float, int, float, float, float]:
        """
        Compute attendance features: a_t, N_late, f_late, delta_a_t, volatility
        
        Returns:
            (cumulative_attendance_rate, late_arrival_count, late_frequency, change, volatility)
        """
        # Query all attendance events for this student in this course
        cursor = self.attendance_events_col.find({
            "user_id": student_id,
            "course_id": course_id,
        }).sort("created_at", 1)
        
        attendance_records = await cursor.to_list(length=1000)
        
        if not attendance_records:
            return 0.0, 0, 0.0, 0.0, 0.0
        
        # Count attendance outcomes
        attended = sum(1 for r in attendance_records if r.get("attendance_marked", False))
        late_arrivals = sum(1 for r in attendance_records if r.get("is_late", False))
        total_sessions = len(attendance_records)
        
        # Cumulative attendance rate: a_t
        cumulative_attendance_rate = attended / total_sessions if total_sessions > 0 else 0.0
        
        # Late arrival frequency: f_late = N_late / total_sessions
        late_frequency = late_arrivals / total_sessions if total_sessions > 0 else 0.0
        
        # Attendance change: delta_a_t (compare last 5 vs first 5 sessions)
        if total_sessions >= 5:
            first_5 = attended_in_range(attendance_records[:5]) / 5
            last_5 = attended_in_range(attendance_records[-5:]) / 5
            attendance_change = last_5 - first_5
        else:
            attendance_change = 0.0
        
        # Attendance volatility: std dev of attendance signal
        # On-time attendance = 1.0, late = 0.5, absent = 0.0
        signals = []
        for r in attendance_records:
            if not r.get("attendance_marked", False):
                signals.append(0.0)  # Absent
            elif r.get("is_late", False):
                signals.append(0.5)  # Late
            else:
                signals.append(1.0)  # On-time
        
        volatility = float(np.std(signals)) if len(signals) > 1 else 0.0
        
        return cumulative_attendance_rate, late_arrivals, late_frequency, attendance_change, volatility
    
    # ========================================================================
    # CURRICULUM FEATURES
    # ========================================================================
    
    async def _compute_curriculum_features(
        self,
        student_id: str,
        course_id: str,
        session_id: str,
        total_topics: int,
    ) -> Tuple[float, float, int]:
        """
        Compute curriculum features: c_t (coverage), coverage trend, topics_behind
        
        Returns:
            (curriculum_coverage, coverage_trend, topics_behind)
        """
        # Query all curriculum events for this student in this course
        cursor = self.curriculum_events_col.find({
            "user_id": student_id,
            "course_id": course_id,
        }).sort("created_at", 1)
        
        curriculum_records = await cursor.to_list(length=1000)
        
        if not curriculum_records:
            return 0.0, 0.0, total_topics
        
        # Unique topics accessed
        topics_accessed = set()
        for r in curriculum_records:
            topic_id = r.get("curriculum_node_id")
            if topic_id:
                topics_accessed.add(topic_id)
        
        # Coverage: fraction of topics accessed
        coverage = len(topics_accessed) / total_topics if total_topics > 0 else 0.0
        
        # Coverage trend: compare first half vs second half
        mid = len(curriculum_records) // 2
        if mid > 0:
            first_half_topics = set(
                r.get("curriculum_node_id") for r in curriculum_records[:mid]
                if r.get("curriculum_node_id")
            )
            second_half_topics = set(
                r.get("curriculum_node_id") for r in curriculum_records[mid:]
                if r.get("curriculum_node_id")
            )
            first_half_coverage = len(first_half_topics) / total_topics if total_topics > 0 else 0.0
            second_half_coverage = len(second_half_topics) / total_topics if total_topics > 0 else 0.0
            coverage_trend = second_half_coverage - first_half_coverage
        else:
            coverage_trend = 0.0
        
        # Topics behind: not yet accessed
        topics_behind = total_topics - len(topics_accessed)
        
        return coverage, coverage_trend, topics_behind
    
    # ========================================================================
    # ENGAGEMENT FEATURES
    # ========================================================================
    
    async def _compute_engagement_features(
        self,
        student_id: str,
        course_id: str,
        session_id: str,
    ) -> Tuple[int, float]:
        """
        Compute engagement features: resource_access_count, biometric_success_rate
        
        Returns:
            (resource_access_count, biometric_success_rate)
        """
        # Resource accesses for this student in this course
        access_cursor = self.resource_accesses_col.find({
            "user_id": student_id,
            "session_id": session_id,
        })
        
        resource_accesses = await access_cursor.to_list(length=1000)
        resource_access_count = len(resource_accesses)
        
        # Biometric success rate: fraction of attendance_verified=True
        attendance_cursor = self.attendance_events_col.find({
            "user_id": student_id,
            "course_id": course_id,
        })
        
        attendance_records = await attendance_cursor.to_list(length=1000)
        
        if not attendance_records:
            biometric_success_rate = 0.0
        else:
            successful = sum(1 for r in attendance_records if r.get("attendance_marked", False))
            biometric_success_rate = successful / len(attendance_records)
        
        return resource_access_count, biometric_success_rate
    
    # ========================================================================
    # TEMPORAL FEATURES
    # ========================================================================
    
    async def _compute_temporal_features(
        self,
        course_metadata: CourseMetadata,
    ) -> Tuple[int, int, bool]:
        """
        Compute temporal features: days_since_start, weeks_into_semester, is_late_in_semester
        
        Returns:
            (days_since_start, weeks_into_semester, is_late_in_semester)
        """
        now = datetime.now(timezone.utc)
        days_since_start = (now - course_metadata.start_date).days
        weeks_into_semester = days_since_start // 7
        
        course_duration = (course_metadata.end_date - course_metadata.start_date).days
        progress = days_since_start / course_duration if course_duration > 0 else 0.0
        is_late_in_semester = progress > 0.8
        
        return days_since_start, weeks_into_semester, is_late_in_semester
    
    # ========================================================================
    # FEATURE COMPUTATION ORCHESTRATOR
    # ========================================================================
    
    async def extract_features_for_session(
        self,
        session_id: str,
        course_id: str,
    ) -> FeatureExtractionResult:
        """
        Extract features for all students in a course after a session.
        
        Args:
            session_id: Attendance session ID
            course_id: Course ID
        
        Returns:
            FeatureExtractionResult with all computed features
        """
        # Get course metadata
        course_doc = await self.courses_col.find_one({"course_id": course_id})
        if not course_doc:
            logger.warning(f"Course not found: {course_id}")
            return FeatureExtractionResult(
                course_id=course_id,
                session_id=session_id,
                student_features=[],
                feature_count=0,
                missing_students=0,
            )
        
        course_metadata = CourseMetadata(
            course_id=course_id,
            course_name=course_doc.get("name", ""),
            total_sessions=course_doc.get("total_sessions", 0),
            total_curriculum_topics=course_doc.get("total_topics", 0),
            start_date=course_doc.get("start_date", datetime.now(timezone.utc)),
            end_date=course_doc.get("end_date", datetime.now(timezone.utc)),
        )
        
        # Get all enrolled students for this course
        cursor = self.users_col.find({
            "enrolled_courses": course_id,
            "role": "student",
        })
        
        students = await cursor.to_list(length=10000)
        
        student_features_list = []
        
        for student_doc in students:
            student_id = student_doc["user_id"]
            
            try:
                # Compute all feature groups
                att_rate, late_count, late_freq, att_change, volatility = \
                    await self._compute_attendance_features(student_id, course_id, session_id)
                
                coverage, coverage_trend, topics_behind = \
                    await self._compute_curriculum_features(
                        student_id, course_id, session_id,
                        course_metadata.total_curriculum_topics
                    )
                
                resource_count, biometric_rate = \
                    await self._compute_engagement_features(student_id, course_id, session_id)
                
                days_since, weeks_into, is_late = \
                    await self._compute_temporal_features(course_metadata)
                
                # Create feature object
                features = StudentFeatures(
                    student_id=student_id,
                    course_id=course_id,
                    session_id=session_id,
                    cumulative_attendance_rate=att_rate,
                    late_arrival_count=late_count,
                    late_arrival_frequency=late_freq,
                    attendance_change=att_change,
                    attendance_volatility=volatility,
                    curriculum_coverage=coverage,
                    curriculum_coverage_trend=coverage_trend,
                    topics_behind=topics_behind,
                    resource_access_count=resource_count,
                    biometric_success_rate=biometric_rate,
                    days_since_start=days_since,
                    weeks_into_semester=weeks_into,
                    is_late_in_semester=is_late,
                )
                
                student_features_list.append(features)
                
            except Exception as e:
                logger.error(f"Error computing features for {student_id}: {e}", exc_info=True)
        
        # Store features in feature_store collection
        for features in student_features_list:
            doc = features.dict()
            doc["_id"] = ObjectId()
            
            # Upsert (replace if exists)
            await self.feature_store_col.update_one(
                {
                    "student_id": features.student_id,
                    "course_id": features.course_id,
                    "session_id": features.session_id,
                },
                {"$set": doc},
                upsert=True,
            )
        
        result = FeatureExtractionResult(
            course_id=course_id,
            session_id=session_id,
            student_features=student_features_list,
            feature_count=len(student_features_list),
            missing_students=len(students) - len(student_features_list),
        )
        
        logger.info(
            f"✓ Feature extraction complete: {len(student_features_list)} students, {result.missing_students} missing",
            extra={"course_id": course_id, "session_id": session_id}
        )
        
        return result
    
    # ========================================================================
    # QUERY & ANALYTICS
    # ========================================================================
    
    async def get_features_for_student(
        self,
        student_id: str,
        course_id: str,
    ) -> Optional[StudentFeatures]:
        """Get latest features for a student in a course."""
        doc = await self.feature_store_col.find_one(
            {
                "student_id": student_id,
                "course_id": course_id,
            },
            sort=[("computed_at", -1)],
        )
        
        if doc:
            doc.pop("_id", None)
            return StudentFeatures(**doc)
        return None
    
    async def get_feature_cohort(
        self,
        course_id: str,
        session_id: str,
    ) -> List[StudentFeatures]:
        """Get all features for a cohort."""
        cursor = self.feature_store_col.find({
            "course_id": course_id,
            "session_id": session_id,
        }).sort("cumulative_attendance_rate", -1)
        
        docs = await cursor.to_list(length=10000)
        
        return [StudentFeatures(**{**d, "_id": None}) for d in docs if "_id" in d]
    
    async def get_at_risk_students(
        self,
        course_id: str,
        threshold_attendance: float = 0.75,
        threshold_coverage: float = 0.50,
    ) -> List[Dict[str, Any]]:
        """Get students below thresholds (at-risk indicators)."""
        cursor = self.feature_store_col.find({
            "course_id": course_id,
            "$or": [
                {"cumulative_attendance_rate": {"$lt": threshold_attendance}},
                {"curriculum_coverage": {"$lt": threshold_coverage}},
            ]
        }).sort("cumulative_attendance_rate", 1)
        
        return await cursor.to_list(length=10000)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def attended_in_range(records: List[Dict]) -> int:
    """Count attended sessions in a list of records."""
    return sum(1 for r in records if r.get("attendance_marked", False))
