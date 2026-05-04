"""
Session and Nonce Management: Replay attack prevention.

Implements short-lived lecture nonces tied to specific:
- Session (attendance event)
- User
- Device
- Time window

Nonce is used ONCE and expires after 5-10 minutes.
Prevents: replay attacks, session fixation, device spoofing.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging
import secrets

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class AttendanceSession(BaseModel):
    """Short-lived attendance session (one lecture)."""
    session_id: str
    course_id: str
    faculty_id: str
    geofence_id: str
    # Session timing
    started_at: datetime
    expires_at: datetime  # When session closes
    # Session metadata
    lecture_title: Optional[str] = None
    expected_duration_minutes: int = 50  # Typical lecture
    # Attendance
    expected_students: int = 0
    checked_in_students: int = 0
    # Security
    is_active: bool = True


class SessionNonce(BaseModel):
    """
    Short-lived nonce bound to session, user, device, and time window.
    
    One-time use token for biometric verification.
    Cannot be replayed even if captured.
    """
    nonce: str
    session_id: str
    user_id: str
    device_id: str
    # Validity window (tight: 5-10 minutes)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    # Usage tracking
    used: bool = False
    used_at: Optional[datetime] = None
    # Security
    attempt_count: int = 0  # Failed verification attempts


class NonceAuditLog(BaseModel):
    """Audit log for nonce lifecycle events."""
    nonce_hash: str  # SHA256 of nonce (don't log raw nonce)
    event: str  # "created", "validated", "used", "expired", "failed"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str
    user_id: str
    device_id: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# SESSION & NONCE MANAGER
# ============================================================================

class SessionNonceManager:
    """
    Manages session and nonce lifecycle.
    
    Lifecycle:
    1. Faculty starts attendance session
    2. Session ID passed to students
    3. Each student: request nonce bound to (session, user, device, time)
    4. Student submits biometric with nonce
    5. Nonce validated once, then deleted (one-time use)
    6. Faculty can review attendance after session expires
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.sessions_col: AsyncIOMotorCollection = db["attendance_sessions"]
        self.nonces_col: AsyncIOMotorCollection = db["session_nonces"]
        self.nonce_audit_col: AsyncIOMotorCollection = db["nonce_audit_logs"]
    
    async def initialize(self):
        """Setup session and nonce collection indexes."""
        # Sessions
        await self.sessions_col.create_index("session_id", unique=True)
        await self.sessions_col.create_index("course_id")
        await self.sessions_col.create_index("faculty_id")
        await self.sessions_col.create_index("expires_at")
        # TTL: Delete expired sessions after 7 days
        await self.sessions_col.create_index(
            "started_at",
            expireAfterSeconds=604800  # 7 days
        )
        
        # Nonces
        await self.nonces_col.create_index("nonce", unique=True, sparse=True)
        await self.nonces_col.create_index("session_id")
        await self.nonces_col.create_index("user_id")
        await self.nonces_col.create_index("device_id")
        # TTL: Auto-expire nonces after validity window
        await self.nonces_col.create_index(
            "expires_at",
            expireAfterSeconds=0  # Delete immediately at expiry
        )
        
        # Audit
        await self.nonce_audit_col.create_index("nonce_hash")
        await self.nonce_audit_col.create_index("session_id")
        await self.nonce_audit_col.create_index("timestamp")
        # TTL: Keep audit logs 90 days
        await self.nonce_audit_col.create_index(
            "timestamp",
            expireAfterSeconds=7776000  # 90 days
        )
        
        logger.info("Session and nonce manager initialized")
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    async def create_session(
        self,
        course_id: str,
        faculty_id: str,
        geofence_id: str,
        lecture_title: Optional[str] = None,
        duration_minutes: int = 50,
        expected_students: int = 0,
    ) -> AttendanceSession:
        """
        Create new attendance session (faculty starts class).
        
        Args:
            course_id: Course ID
            faculty_id: Faculty ID
            geofence_id: Room/building ID
            lecture_title: Title of lecture
            duration_minutes: Expected session duration (50 for typical lecture)
            expected_students: Enrollment count
        
        Returns:
            AttendanceSession
        """
        session_id = self._generate_session_id()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=duration_minutes)
        
        session = AttendanceSession(
            session_id=session_id,
            course_id=course_id,
            faculty_id=faculty_id,
            geofence_id=geofence_id,
            started_at=now,
            expires_at=expires_at,
            lecture_title=lecture_title,
            expected_duration_minutes=duration_minutes,
            expected_students=expected_students,
        )
        
        # Store in database
        doc = session.dict()
        doc["_id"] = ObjectId()
        await self.sessions_col.insert_one(doc)
        
        logger.info(
            f"Attendance session created: {session_id}",
            extra={
                "course_id": course_id,
                "expected_duration": duration_minutes,
                "expected_students": expected_students,
            }
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[AttendanceSession]:
        """Retrieve session."""
        doc = await self.sessions_col.find_one({"session_id": session_id})
        if doc:
            doc.pop("_id", None)
            return AttendanceSession(**doc)
        return None
    
    async def is_session_active(self, session_id: str) -> bool:
        """Check if session is still active."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        now = datetime.now(timezone.utc)
        return (
            session.is_active and
            now < session.expires_at
        )
    
    async def close_session(self, session_id: str):
        """Faculty closes session (no more check-ins allowed)."""
        await self.sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {"is_active": False}}
        )
        logger.info(f"Session closed: {session_id}")
    
    # ========================================================================
    # NONCE MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session ID."""
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def _generate_nonce() -> str:
        """Generate cryptographic nonce (one-time token)."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def _hash_nonce(nonce: str) -> str:
        """Hash nonce for audit logging (don't log raw nonce)."""
        import hashlib
        return hashlib.sha256(nonce.encode()).hexdigest()
    
    async def create_nonce(
        self,
        session_id: str,
        user_id: str,
        device_id: str,
        validity_seconds: int = 300,  # 5 minutes default
    ) -> SessionNonce:
        """
        Create short-lived nonce for student check-in.
        
        Nonce is bound to:
        - Specific session (can't reuse for different class)
        - Specific user (can't transfer to another student)
        - Specific device (can't use from different phone)
        - Tight time window (5-10 minutes, typically)
        
        Args:
            session_id: Attendance session ID
            user_id: Student ID
            device_id: Device ID
            validity_seconds: How long nonce is valid (default 5 min)
        
        Returns:
            SessionNonce with nonce and expiry
        
        Raises:
            ValueError: If session not active
        """
        # Verify session is active
        if not await self.is_session_active(session_id):
            raise ValueError(f"Session not active: {session_id}")
        
        # Generate nonce
        nonce = self._generate_nonce()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=validity_seconds)
        
        nonce_record = SessionNonce(
            nonce=nonce,
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            created_at=now,
            expires_at=expires_at,
        )
        
        # Store in database
        doc = nonce_record.dict()
        doc["_id"] = ObjectId()
        await self.nonces_col.insert_one(doc)
        
        # Audit
        await self._audit_nonce(nonce, "created", session_id, user_id, device_id)
        
        logger.debug(
            f"Nonce created for session {session_id}",
            extra={"user_id": user_id, "validity_seconds": validity_seconds}
        )
        
        return nonce_record
    
    async def validate_nonce(
        self,
        nonce: str,
        session_id: str,
        user_id: str,
        device_id: str,
    ) -> bool:
        """
        Validate nonce and mark as used (one-time use).
        
        Checks:
        1. Nonce exists
        2. Nonce not expired
        3. Nonce bindings match (session, user, device)
        4. Nonce not already used
        
        Args:
            nonce: Nonce to validate
            session_id, user_id, device_id: Must match nonce bindings
        
        Returns:
            True if valid and fresh
        
        Raises:
            ValueError: If nonce invalid for any reason
        """
        nonce_record = await self.nonces_col.find_one({"nonce": nonce})
        
        if not nonce_record:
            await self._audit_nonce(nonce, "failed", session_id, user_id, device_id,
                                   {"error": "Nonce not found"})
            raise ValueError("Nonce not found (invalid or already used)")
        
        # Check bindings
        if nonce_record["session_id"] != session_id:
            await self._audit_nonce(nonce, "failed", session_id, user_id, device_id,
                                   {"error": "Session mismatch"})
            raise ValueError("Nonce session_id mismatch (session fixation attempt?)")
        
        if nonce_record["user_id"] != user_id:
            await self._audit_nonce(nonce, "failed", session_id, user_id, device_id,
                                   {"error": "User mismatch"})
            raise ValueError("Nonce user_id mismatch (identity spoofing attempt?)")
        
        if nonce_record["device_id"] != device_id:
            await self._audit_nonce(nonce, "failed", session_id, user_id, device_id,
                                   {"error": "Device mismatch"})
            raise ValueError("Nonce device_id mismatch (device spoofing attempt?)")
        
        # Check expiry
        if nonce_record["expires_at"] < datetime.now(timezone.utc):
            await self._audit_nonce(nonce, "expired", session_id, user_id, device_id)
            raise ValueError("Nonce expired (check-in took too long?)")
        
        # Check if already used
        if nonce_record["used"]:
            await self._audit_nonce(nonce, "failed", session_id, user_id, device_id,
                                   {"error": "Already used (replay attack?)"})
            raise ValueError("Nonce already used (replay attack?)")
        
        # Mark as used (delete to prevent reuse)
        await self.nonces_col.delete_one({"nonce": nonce})
        
        # Audit
        await self._audit_nonce(nonce, "used", session_id, user_id, device_id)
        
        logger.info(
            f"Nonce validated and consumed",
            extra={"session_id": session_id, "user_id": user_id}
        )
        
        return True
    
    async def check_nonce_rate_limit(
        self,
        user_id: str,
        device_id: str,
        max_nonces_per_hour: int = 20,
    ) -> bool:
        """
        Check if user/device exceeded nonce request rate limit.
        
        Prevents brute-force attacks (student requesting thousands of nonces).
        """
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        count = await self.nonces_col.count_documents({
            "user_id": user_id,
            "device_id": device_id,
            "created_at": {"$gte": one_hour_ago},
        })
        
        if count >= max_nonces_per_hour:
            logger.warning(f"Nonce rate limit exceeded: {user_id} on {device_id}")
            return False
        
        return True
    
    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================
    
    async def _audit_nonce(
        self,
        nonce: str,
        event: str,
        session_id: str,
        user_id: str,
        device_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Audit nonce lifecycle event."""
        nonce_hash = self._hash_nonce(nonce)
        
        audit_log = NonceAuditLog(
            nonce_hash=nonce_hash,
            event=event,
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            details=details or {},
        )
        
        doc = audit_log.dict()
        doc["_id"] = ObjectId()
        await self.nonce_audit_col.insert_one(doc)
    
    async def get_nonce_audit_trail(
        self,
        session_id: str,
    ) -> list:
        """Retrieve nonce audit trail for session."""
        cursor = self.nonce_audit_col.find({"session_id": session_id}).sort("timestamp", -1)
        return await cursor.to_list(length=1000)
    
    # ========================================================================
    # SESSION STATISTICS
    # ========================================================================
    
    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get attendance statistics for session."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Count check-ins
        attendance_col = self.db["attendance_events"]
        checked_in = await attendance_col.count_documents({
            "session_id": session_id,
            "status": "marked",
        })
        
        # Count nonce audits
        nonce_attempts = await self.nonce_audit_col.count_documents({
            "session_id": session_id,
        })
        
        failed_attempts = await self.nonce_audit_col.count_documents({
            "session_id": session_id,
            "event": "failed",
        })
        
        return {
            "session_id": session_id,
            "course_id": session.course_id,
            "started_at": session.started_at,
            "expires_at": session.expires_at,
            "is_active": session.is_active,
            "expected_students": session.expected_students,
            "checked_in": checked_in,
            "attendance_rate": checked_in / session.expected_students if session.expected_students > 0 else 0.0,
            "nonce_attempts": nonce_attempts,
            "nonce_failures": failed_attempts,
            "nonce_success_rate": (nonce_attempts - failed_attempts) / nonce_attempts if nonce_attempts > 0 else 0.0,
        }


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create attendance session."""
    course_id: str
    geofence_id: str
    lecture_title: Optional[str] = None
    duration_minutes: int = 50
    expected_students: int = 0


class CreateSessionResponse(BaseModel):
    """Response with session ID."""
    session_id: str
    started_at: datetime
    expires_at: datetime
    expected_duration_minutes: int


class RequestNonceRequest(BaseModel):
    """Student requests nonce for check-in."""
    session_id: str
    device_id: str


class RequestNonceResponse(BaseModel):
    """Response with nonce."""
    nonce: str
    expires_in_seconds: int
    session_id: str
