"""
Collusion Detector: Graph-based anomaly detection for suspicious behavior patterns.

Formula: eta_i_j = (1 / T) * sum_{t=1 to T} [z_i(t) == z_j(t)] + lambda * d_i_j

Detects students exhibiting suspiciously similar behavior (potential collusion).

Components:
- z_i(t) = behavior state of student i at time t (attendance, curriculum, biometric outcomes)
- eta_i_j = structural similarity between students i and j
- d_i_j = behavioral distance (dissimilarity)
- lambda = weight for distance term
- T = number of sessions

Behavior States:
- z_i(t) ∈ {on_time_pass, late_pass, absent, absent_excused}

High eta_i_j indicates suspicious similarity:
- Similar attendance patterns
- Similar biometric verification outcomes
- Similar curriculum access patterns
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class BehaviorState(str):
    """Behavioral state at session t."""
    ON_TIME_PASS = "on_time_pass"  # On-time attendance, biometric pass
    LATE_PASS = "late_pass"  # Late arrival, biometric pass
    ABSENT = "absent"  # Absent (no biometric attempt)
    ABSENT_EXCUSED = "absent_excused"  # Excused absence
    ON_TIME_FAIL = "on_time_fail"  # On-time but biometric failed
    LATE_FAIL = "late_fail"  # Late arrival, biometric failed


class StudentBehaviorProfile(BaseModel):
    """Historical behavior profile for a student."""
    student_id: str
    course_id: str
    behavior_sequence: List[str]  # [z_i(1), z_i(2), ..., z_i(T)]
    sessions_count: int
    on_time_pass_count: int
    late_pass_count: int
    absent_count: int
    curriculum_access_pattern: List[int]  # Which topics accessed each session
    biometric_pass_rate: float
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CollusionPair(BaseModel):
    """Pair of students with high structural similarity."""
    student_pair_id: str
    student_i_id: str
    student_j_id: str
    course_id: str
    # Similarity metrics
    sequence_similarity: float = Field(ge=0.0, le=1.0)  # Overlap in behavior states
    distance_term: float = Field(ge=0.0, le=1.0)  # Behavioral distance
    structural_similarity: float = Field(ge=0.0, le=1.0)  # eta_i_j
    # Evidence
    matching_sessions: int  # Count of sessions with same behavior state
    total_sessions: int
    # Risk flag
    is_suspicious: bool
    confidence: float = Field(ge=0.0, le=1.0)
    # Metadata
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnomalyDetectionReport(BaseModel):
    """Report of detected anomalies and suspicious behavior."""
    course_id: str
    report_id: str
    analysis_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Totals
    students_analyzed: int
    suspicious_pairs: int
    high_risk_pairs: int
    # Top flagged pairs
    top_pairs: List[CollusionPair]
    # Recommendations
    investigation_recommendations: List[str]


# ============================================================================
# COLLUSION DETECTOR
# ============================================================================

class CollusionDetector:
    """
    Graph-based anomaly detection for collusion.
    
    Detects suspiciously similar behavior patterns between students:
    - Similar attendance patterns
    - Similar biometric verification outcomes
    - Similar curriculum access timing
    
    Formula: eta_i_j = (1/T) * sum_{t=1 to T} [z_i(t) == z_j(t)] + lambda * d_i_j
    
    Where:
    - First term: fraction of sessions with same behavior state
    - Second term: behavioral distance (penalty for dissimilarity)
    - High eta_i_j → suspicious pair
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        lambda_distance: float = 0.3,  # Weight for distance term
        similarity_threshold: float = 0.75,  # Flag if eta_i_j > threshold
    ):
        self.db = db
        self.lambda_weight = lambda_distance
        self.similarity_threshold = similarity_threshold
        self.behavior_profiles_col: AsyncIOMotorCollection = db["behavior_profiles"]
        self.collusion_pairs_col: AsyncIOMotorCollection = db["collusion_pairs"]
        self.anomaly_reports_col: AsyncIOMotorCollection = db["anomaly_reports"]
    
    async def initialize(self):
        """Setup collection indexes."""
        await self.behavior_profiles_col.create_index("student_id")
        await self.behavior_profiles_col.create_index("course_id")
        await self.behavior_profiles_col.create_index([("student_id", 1), ("course_id", 1)], unique=True)
        
        await self.collusion_pairs_col.create_index("student_pair_id", unique=True)
        await self.collusion_pairs_col.create_index("course_id")
        await self.collusion_pairs_col.create_index("structural_similarity", 1)
        await self.collusion_pairs_col.create_index("is_suspicious")
        
        await self.anomaly_reports_col.create_index("course_id")
        await self.anomaly_reports_col.create_index("analysis_date", -1)
        
        logger.info("Collusion detector initialized")
    
    # ========================================================================
    # BEHAVIOR PROFILE EXTRACTION
    # ========================================================================
    
    async def build_behavior_profiles(
        self,
        course_id: str,
    ) -> List[StudentBehaviorProfile]:
        """
        Build behavior profiles for all students in course.
        
        Args:
            course_id: Course ID
        
        Returns:
            List of StudentBehaviorProfile objects
        """
        # Query all attendance events for this course (sorted by time)
        attendance_cursor = self.db["attendance_events"].find({
            "course_id": course_id,
        }).sort("created_at", 1)
        
        attendance_events = await attendance_cursor.to_list(length=10000)
        
        if not attendance_events:
            return []
        
        # Group by student
        profiles_dict: Dict[str, Dict] = defaultdict(lambda: {
            "behavior_sequence": [],
            "sessions_count": 0,
            "on_time_pass": 0,
            "late_pass": 0,
            "absent": 0,
            "curriculum_nodes": set(),
            "biometric_passes": 0,
            "total_attempts": 0,
        })
        
        for event in attendance_events:
            user_id = event.get("user_id")
            is_attended = event.get("attendance_marked", False)
            is_late = event.get("is_late", False)
            biometric_success = event.get("biometric_success", False)
            
            # Determine behavior state
            if not is_attended:
                if event.get("is_excused", False):
                    state = BehaviorState.ABSENT_EXCUSED
                else:
                    state = BehaviorState.ABSENT
            elif is_late and biometric_success:
                state = BehaviorState.LATE_PASS
            elif is_late and not biometric_success:
                state = BehaviorState.LATE_FAIL
            elif not is_late and biometric_success:
                state = BehaviorState.ON_TIME_PASS
            else:
                state = BehaviorState.ON_TIME_FAIL
            
            profiles_dict[user_id]["behavior_sequence"].append(state)
            profiles_dict[user_id]["sessions_count"] += 1
            
            # Count state types
            if state == BehaviorState.ON_TIME_PASS:
                profiles_dict[user_id]["on_time_pass"] += 1
                profiles_dict[user_id]["biometric_passes"] += 1
            elif state == BehaviorState.LATE_PASS:
                profiles_dict[user_id]["late_pass"] += 1
                profiles_dict[user_id]["biometric_passes"] += 1
            elif state == BehaviorState.ABSENT:
                profiles_dict[user_id]["absent"] += 1
            
            if biometric_success:
                profiles_dict[user_id]["total_attempts"] += 1
        
        # Convert to StudentBehaviorProfile objects
        profiles = []
        for user_id, data in profiles_dict.items():
            biometric_rate = (
                data["biometric_passes"] / data["total_attempts"]
                if data["total_attempts"] > 0 else 0.0
            )
            
            profile = StudentBehaviorProfile(
                student_id=user_id,
                course_id=course_id,
                behavior_sequence=data["behavior_sequence"],
                sessions_count=data["sessions_count"],
                on_time_pass_count=data["on_time_pass"],
                late_pass_count=data["late_pass"],
                absent_count=data["absent"],
                curriculum_access_pattern=[],  # TODO: could add curriculum data
                biometric_pass_rate=biometric_rate,
            )
            
            profiles.append(profile)
            
            # Store in database
            doc = profile.dict()
            doc["_id"] = ObjectId()
            await self.behavior_profiles_col.update_one(
                {
                    "student_id": user_id,
                    "course_id": course_id,
                },
                {"$set": doc},
                upsert=True,
            )
        
        logger.info(f"Built behavior profiles for {len(profiles)} students")
        return profiles
    
    # ========================================================================
    # SIMILARITY COMPUTATION
    # ========================================================================
    
    def _compute_sequence_similarity(
        self,
        seq_i: List[str],
        seq_j: List[str],
    ) -> Tuple[float, int]:
        """
        Compute sequence similarity: fraction of matching states.
        
        Returns:
            (similarity_score, matching_count)
        """
        if len(seq_i) == 0 or len(seq_j) == 0:
            return 0.0, 0
        
        # Align sequences (use minimum length)
        min_len = min(len(seq_i), len(seq_j))
        
        matching = sum(1 for t in range(min_len) if seq_i[t] == seq_j[t])
        similarity = matching / min_len if min_len > 0 else 0.0
        
        return similarity, matching
    
    def _compute_behavioral_distance(
        self,
        profile_i: StudentBehaviorProfile,
        profile_j: StudentBehaviorProfile,
    ) -> float:
        """
        Compute behavioral distance: how dissimilar are overall behavior patterns?
        
        Returns:
            Distance [0, 1] (0 = identical, 1 = completely different)
        """
        # Compare attendance patterns
        on_time_diff = abs(profile_i.on_time_pass_count - profile_j.on_time_pass_count) / max(
            profile_i.sessions_count, profile_j.sessions_count, 1
        )
        late_diff = abs(profile_i.late_pass_count - profile_j.late_pass_count) / max(
            profile_i.sessions_count, profile_j.sessions_count, 1
        )
        absent_diff = abs(profile_i.absent_count - profile_j.absent_count) / max(
            profile_i.sessions_count, profile_j.sessions_count, 1
        )
        
        # Compare biometric success rates
        biometric_diff = abs(profile_i.biometric_pass_rate - profile_j.biometric_pass_rate)
        
        # Weighted average
        distance = 0.3 * on_time_diff + 0.2 * late_diff + 0.2 * absent_diff + 0.3 * biometric_diff
        
        return float(np.clip(distance, 0.0, 1.0))
    
    def compute_structural_similarity(
        self,
        profile_i: StudentBehaviorProfile,
        profile_j: StudentBehaviorProfile,
    ) -> Tuple[float, int]:
        """
        Compute structural similarity: eta_i_j
        
        Formula: eta_i_j = (1/T) * sum_{t=1 to T} [z_i(t) == z_j(t)] + lambda * d_i_j
        
        Returns:
            (structural_similarity, matching_sessions)
        """
        # First term: sequence similarity
        seq_similarity, matching = self._compute_sequence_similarity(
            profile_i.behavior_sequence,
            profile_j.behavior_sequence,
        )
        
        # Second term: behavioral distance (penalty)
        distance = self._compute_behavioral_distance(profile_i, profile_j)
        
        # Combined score
        eta_i_j = seq_similarity + self.lambda_weight * distance
        
        # Clip to [0, 1]
        eta_i_j = float(np.clip(eta_i_j, 0.0, 1.0))
        
        return eta_i_j, matching
    
    # ========================================================================
    # PAIR DETECTION
    # ========================================================================
    
    async def detect_collusion_pairs(
        self,
        course_id: str,
        profiles: Optional[List[StudentBehaviorProfile]] = None,
    ) -> List[CollusionPair]:
        """
        Detect all suspicious pairs in a course.
        
        Args:
            course_id: Course ID
            profiles: Pre-computed behavior profiles (if None, will build them)
        
        Returns:
            List of CollusionPair objects with eta_i_j >= threshold
        """
        if profiles is None:
            profiles = await self.build_behavior_profiles(course_id)
        
        if len(profiles) < 2:
            return []
        
        suspicious_pairs = []
        
        # Compare all pairs
        for i in range(len(profiles)):
            for j in range(i + 1, len(profiles)):
                profile_i = profiles[i]
                profile_j = profiles[j]
                
                # Compute similarity
                eta_i_j, matching_sessions = self.compute_structural_similarity(profile_i, profile_j)
                
                # Check if suspicious
                is_suspicious = eta_i_j >= self.similarity_threshold
                
                if is_suspicious or eta_i_j > 0.5:  # Store moderate-to-high similarities
                    total_sessions = max(
                        profile_i.sessions_count,
                        profile_j.sessions_count,
                    )
                    
                    pair = CollusionPair(
                        student_pair_id=f"pair_{profile_i.student_id}_{profile_j.student_id}",
                        student_i_id=profile_i.student_id,
                        student_j_id=profile_j.student_id,
                        course_id=course_id,
                        sequence_similarity=float(matching_sessions / total_sessions) if total_sessions > 0 else 0.0,
                        distance_term=self._compute_behavioral_distance(profile_i, profile_j),
                        structural_similarity=eta_i_j,
                        matching_sessions=matching_sessions,
                        total_sessions=total_sessions,
                        is_suspicious=is_suspicious,
                        confidence=eta_i_j,
                    )
                    
                    suspicious_pairs.append(pair)
                    
                    # Store in database
                    doc = pair.dict()
                    doc["_id"] = ObjectId()
                    await self.collusion_pairs_col.update_one(
                        {"student_pair_id": pair.student_pair_id},
                        {"$set": doc},
                        upsert=True,
                    )
        
        # Sort by similarity (highest first)
        suspicious_pairs.sort(key=lambda p: p.structural_similarity, reverse=True)
        
        logger.info(
            f"Detected {len([p for p in suspicious_pairs if p.is_suspicious])} suspicious pairs "
            f"out of {len(suspicious_pairs)} total flagged"
        )
        
        return suspicious_pairs
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    async def generate_anomaly_report(
        self,
        course_id: str,
        top_k: int = 10,
    ) -> AnomalyDetectionReport:
        """
        Generate anomaly detection report for a course.
        
        Args:
            course_id: Course ID
            top_k: Show top K suspicious pairs
        
        Returns:
            AnomalyDetectionReport
        """
        # Build profiles
        profiles = await self.build_behavior_profiles(course_id)
        
        # Detect suspicious pairs
        suspicious_pairs = await self.detect_collusion_pairs(course_id, profiles)
        
        # Filter to truly suspicious
        high_risk = [p for p in suspicious_pairs if p.is_suspicious]
        
        # Get top pairs
        top_pairs = high_risk[:top_k]
        
        # Generate recommendations
        recommendations = []
        for i, pair in enumerate(top_pairs):
            rec = (
                f"Pair {i+1}: Students {pair.student_i_id} and {pair.student_j_id} "
                f"show {pair.structural_similarity:.1%} structural similarity "
                f"({pair.matching_sessions}/{pair.total_sessions} matching sessions). "
                f"Consider manual review of attendance patterns and biometric records."
            )
            recommendations.append(rec)
        
        report = AnomalyDetectionReport(
            course_id=course_id,
            report_id=f"report_{course_id}_{datetime.now(timezone.utc).timestamp()}",
            students_analyzed=len(profiles),
            suspicious_pairs=len(high_risk),
            high_risk_pairs=len([p for p in high_risk if p.structural_similarity > 0.85]),
            top_pairs=top_pairs,
            investigation_recommendations=recommendations,
        )
        
        # Store report
        doc = report.dict(exclude={"top_pairs"})
        doc["_id"] = ObjectId()
        doc["top_pairs"] = [p.dict() for p in report.top_pairs]
        await self.anomaly_reports_col.insert_one(doc)
        
        logger.info(
            f"Generated anomaly report: {report.suspicious_pairs} suspicious pairs detected",
            extra={"course_id": course_id}
        )
        
        return report
