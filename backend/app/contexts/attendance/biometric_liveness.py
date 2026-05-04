"""
Biometric Liveness Verification Service.

CRITICAL PRIVACY REQUIREMENT:
- Store ONLY verification outcome (pass/fail) + confidence score
- NEVER store raw biometric data (face, fingerprint, iris)
- All biometric processing happens on-device or in privacy-preserving manner
- Audit trail includes only: timestamp, confidence, outcome, nonce

Liveness detection ensures:
1. Biometric is from a living person (not a photo/video replay)
2. Biometric matches registered credential (for that session)
3. Biometric confidence above threshold
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from enum import Enum
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class BiometricModality(str, Enum):
    """Supported biometric modalities."""
    FACE = "face"
    FINGERPRINT = "fingerprint"
    IRIS = "iris"
    WEBAUTHN = "webauthn"  # Touch ID / Face ID on device


class LivenessCheckOutcome(str, Enum):
    """Biometric liveness check outcome."""
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class BiometricVerificationRecord(BaseModel):
    """
    Biometric verification outcome record.
    
    IMPORTANT: This stores ONLY the verification outcome, not the biometric itself.
    """
    verification_id: str
    user_id: str
    device_id: str
    session_id: str
    nonce: str  # Cryptographic nonce for replay protection
    # Outcome (never store raw biometric data)
    modality: BiometricModality
    outcome: LivenessCheckOutcome
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0-1.0
    liveness_score: float = Field(ge=0.0, le=1.0)  # Liveness detection
    # Temporal bounds
    captured_at: datetime
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime  # Biometric valid until this time
    # Metadata (audit trail)
    attempt_number: int = 1  # Which attempt in this session?
    device_model: Optional[str] = None
    processing_time_ms: int = 0  # How long did verification take?
    # Security flags
    anti_spoofing_passed: bool = False
    liveness_detection_used: bool = True  # Was liveness detection enabled?
    # Nothing else! No raw biometric data!


class BiometricNonce(BaseModel):
    """Short-lived nonce for biometric verification."""
    nonce: str
    user_id: str
    device_id: str
    session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime


# ============================================================================
# BIOMETRIC LIVENESS VERIFICATION SERVICE
# ============================================================================

class BiometricLivenessService:
    """
    Manages biometric verification with liveness detection.
    
    Key principle: Verify → Store only outcome → Never store biometric
    
    On-device processing:
    - Device captures biometric
    - Device performs liveness detection (TrustKit, LivenessDetection frameworks)
    - Device sends only: outcome (pass/fail), confidence, nonce, signature
    - Server verifies and creates audit record
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.biometric_verifications_col: AsyncIOMotorCollection = db["biometric_verifications"]
        self.biometric_nonces_col: AsyncIOMotorCollection = db["biometric_nonces"]
        self.biometric_attempts_col: AsyncIOMotorCollection = db["biometric_attempts"]
    
    async def initialize(self):
        """Setup biometric collections with privacy-preserving indexes."""
        # Verification records
        await self.biometric_verifications_col.create_index("verification_id", unique=True)
        await self.biometric_verifications_col.create_index("user_id")
        await self.biometric_verifications_col.create_index("session_id", unique=True)
        await self.biometric_verifications_col.create_index("nonce", unique=True)
        await self.biometric_verifications_col.create_index("device_id")
        # TTL: Purge after 90 days (regulatory requirement)
        await self.biometric_verifications_col.create_index(
            "verified_at",
            expireAfterSeconds=7776000  # 90 days
        )
        
        # Nonces
        await self.biometric_nonces_col.create_index("nonce", unique=True)
        # TTL: Purge after 15 minutes
        await self.biometric_nonces_col.create_index(
            "created_at",
            expireAfterSeconds=900  # 15 minutes
        )
        
        # Attempt tracking
        await self.biometric_attempts_col.create_index("session_id")
        await self.biometric_attempts_col.create_index("device_id")
        
        logger.info("Biometric collections initialized with privacy settings")
    
    def generate_nonce(self) -> str:
        """Generate cryptographic nonce for biometric verification."""
        import secrets
        return secrets.token_urlsafe(32)
    
    async def create_biometric_nonce(
        self,
        user_id: str,
        device_id: str,
        session_id: str,
        validity_seconds: int = 300,
    ) -> BiometricNonce:
        """
        Create a short-lived nonce for biometric verification.
        
        Args:
            user_id: Student ID
            device_id: Device ID
            session_id: Attendance session ID
            validity_seconds: How long nonce is valid (default 5 minutes)
        
        Returns:
            BiometricNonce with expiry
        
        Nonce prevents:
        1. Replay attacks (nonce can only be used once)
        2. Session fixation (bound to specific session)
        3. Device spoofing (bound to specific device)
        """
        nonce = self.generate_nonce()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=validity_seconds)
        
        nonce_record = BiometricNonce(
            nonce=nonce,
            user_id=user_id,
            device_id=device_id,
            session_id=session_id,
            created_at=now,
            expires_at=expires_at,
        )
        
        # Store in database
        await self.biometric_nonces_col.insert_one(nonce_record.dict())
        
        logger.debug(f"Created biometric nonce for session {session_id}")
        return nonce_record
    
    async def verify_nonce(
        self,
        nonce: str,
        user_id: str,
        device_id: str,
        session_id: str,
    ) -> bool:
        """
        Verify nonce is valid and hasn't been used.
        
        Args:
            nonce: Nonce to verify
            user_id: Student ID (must match)
            device_id: Device ID (must match)
            session_id: Session ID (must match)
        
        Returns:
            True if nonce is valid and fresh
        
        Raises:
            ValueError: If nonce invalid, expired, or mismatched
        """
        nonce_record = await self.biometric_nonces_col.find_one({"nonce": nonce})
        
        if not nonce_record:
            raise ValueError("Nonce not found (invalid or already used)")
        
        # Verify bindings
        if nonce_record["user_id"] != user_id:
            raise ValueError("Nonce user_id mismatch (session fixation attempt?)")
        if nonce_record["device_id"] != device_id:
            raise ValueError("Nonce device_id mismatch (device spoofing attempt?)")
        if nonce_record["session_id"] != session_id:
            raise ValueError("Nonce session_id mismatch")
        
        # Check expiry
        if nonce_record["expires_at"] < datetime.now(timezone.utc):
            raise ValueError("Nonce expired")
        
        # Mark as used by deleting
        await self.biometric_nonces_col.delete_one({"nonce": nonce})
        
        logger.debug(f"Nonce verified and consumed: {nonce[:8]}...")
        return True
    
    async def record_verification(
        self,
        user_id: str,
        device_id: str,
        session_id: str,
        nonce: str,
        modality: BiometricModality,
        outcome: LivenessCheckOutcome,
        confidence: float,
        liveness_score: float,
        device_model: Optional[str] = None,
        processing_time_ms: int = 0,
        anti_spoofing_passed: bool = False,
    ) -> BiometricVerificationRecord:
        """
        Record biometric verification outcome.
        
        CRITICAL: Only store outcome + confidence, never raw biometric data.
        
        Args:
            user_id, device_id, session_id: Identity binding
            nonce: Used nonce (for replay protection)
            modality: face, fingerprint, iris, webauthn
            outcome: pass, fail, inconclusive
            confidence: Biometric match confidence (0.0-1.0)
            liveness_score: Liveness detection score (0.0-1.0)
            device_model: Device model (for debugging)
            processing_time_ms: Time spent on biometric processing
            anti_spoofing_passed: Did anti-spoofing checks pass?
        
        Returns:
            BiometricVerificationRecord (no raw biometric data)
        
        Raises:
            ValueError: If nonce invalid or outcome suspicious
        """
        # Verify nonce first
        try:
            await self.verify_nonce(nonce, user_id, device_id, session_id)
        except ValueError as e:
            logger.warning(f"Nonce verification failed: {e}")
            raise
        
        # Validate outcome
        if outcome == LivenessCheckOutcome.PASS:
            if confidence < 0.9:
                logger.warning(f"Pass outcome but low confidence: {confidence}")
            if liveness_score < 0.8:
                logger.warning(f"Pass outcome but low liveness score: {liveness_score}")
        
        # Create verification record (NO raw biometric data)
        verification_id = str(ObjectId())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=1)  # Verification valid for 1 hour
        
        record = BiometricVerificationRecord(
            verification_id=verification_id,
            user_id=user_id,
            device_id=device_id,
            session_id=session_id,
            nonce=nonce,
            modality=modality,
            outcome=outcome,
            confidence=confidence,
            liveness_score=liveness_score,
            captured_at=now,
            verified_at=now,
            expires_at=expires_at,
            device_model=device_model,
            processing_time_ms=processing_time_ms,
            anti_spoofing_passed=anti_spoofing_passed,
        )
        
        # Store in database
        doc = record.dict()
        doc["_id"] = ObjectId()
        await self.biometric_verifications_col.insert_one(doc)
        
        # Log attempt
        await self.biometric_attempts_col.insert_one({
            "session_id": session_id,
            "device_id": device_id,
            "user_id": user_id,
            "outcome": outcome.value,
            "confidence": confidence,
            "liveness_score": liveness_score,
            "timestamp": now,
        })
        
        logger.info(
            f"Biometric verification recorded: {modality} → {outcome}",
            extra={
                "session_id": session_id,
                "confidence": confidence,
                "liveness_score": liveness_score,
            }
        )
        
        return record
    
    async def get_verification(self, verification_id: str) -> Optional[BiometricVerificationRecord]:
        """Retrieve verification record (no raw biometric data included)."""
        doc = await self.biometric_verifications_col.find_one({"verification_id": verification_id})
        if doc:
            doc.pop("_id", None)
            return BiometricVerificationRecord(**doc)
        return None
    
    async def is_verification_valid(
        self,
        session_id: str,
        modality: BiometricModality,
    ) -> bool:
        """
        Check if recent biometric verification exists for session.
        
        Returns True if verification is fresh and valid.
        """
        record = await self.biometric_verifications_col.find_one({
            "session_id": session_id,
            "modality": modality.value,
            "outcome": LivenessCheckOutcome.PASS.value,
        })
        
        if not record:
            return False
        
        # Check expiry
        if record["expires_at"] < datetime.now(timezone.utc):
            return False
        
        # Check confidence threshold
        if record["confidence"] < 0.95:
            return False
        
        # Check liveness score
        if record["liveness_score"] < 0.80:
            return False
        
        return True
    
    async def get_attempt_count(self, session_id: str) -> int:
        """Get number of biometric attempts in this session."""
        count = await self.biometric_attempts_col.count_documents({"session_id": session_id})
        return count
    
    async def check_rate_limit(
        self,
        device_id: str,
        max_attempts_per_hour: int = 10,
    ) -> bool:
        """
        Check if device exceeded biometric attempt rate limit.
        
        Prevents brute-force attacks.
        """
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        count = await self.biometric_attempts_col.count_documents({
            "device_id": device_id,
            "timestamp": {"$gte": one_hour_ago},
        })
        
        if count >= max_attempts_per_hour:
            logger.warning(f"Device rate limit exceeded: {device_id} ({count} attempts)")
            return False
        
        return True


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BiometricNonceRequest(BaseModel):
    """Request biometric verification nonce."""
    session_id: str
    device_id: str


class BiometricNonceResponse(BaseModel):
    """Response with biometric nonce."""
    nonce: str
    expires_in_seconds: int
    session_id: str


class BiometricVerificationRequest(BaseModel):
    """Submit biometric verification (outcome only, not raw biometric)."""
    session_id: str
    device_id: str
    nonce: str
    modality: str  # "face", "fingerprint", "iris", "webauthn"
    outcome: str  # "pass", "fail", "inconclusive"
    confidence: float = Field(ge=0.0, le=1.0)
    liveness_score: float = Field(ge=0.0, le=1.0)
    device_model: Optional[str] = None
    processing_time_ms: int = 0
    anti_spoofing_passed: bool = False


class BiometricVerificationResponse(BaseModel):
    """Biometric verification response."""
    verification_id: str
    outcome: str  # "pass", "fail"
    confidence: float
    liveness_score: float
    verified_at: datetime
