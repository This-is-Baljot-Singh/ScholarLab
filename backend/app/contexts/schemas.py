"""
Core domain models and MongoDB collection schemas for ScholarLab.

Key principle: Separate HIGH-FREQUENCY, IMMUTABLE event collections
from MUTABLE profile/state collections.

Collections:
- users (mutable: profile, auth state)
- devices (mutable: device registry)
- sessions (mutable: active sessions)
- rooms (mutable: venue metadata)
- courses (mutable: curriculum structure)
- attendance_events (IMMUTABLE append-only)
- curriculum_events (IMMUTABLE append-only)
- risk_events (IMMUTABLE append-only)
- audit_logs (IMMUTABLE append-only, signed)
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from bson import ObjectId


# ============================================================================
# IDENTITY MODELS
# ============================================================================

class RoleEnum(str, Enum):
    student = "student"
    faculty = "faculty"
    admin = "admin"


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    full_name: str
    role: RoleEnum


class UserInDB(UserBase):
    """User stored in MongoDB."""
    id: str = Field(alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # WebAuthn credentials
    webauthn_credentials: List[Dict[str, Any]] = []
    # Current challenge for biometric verification
    current_challenge: Optional[str] = None
    challenge_expiry: Optional[datetime] = None
    # Metadata
    is_active: bool = True
    metadata: Dict[str, Any] = {}

    class Config:
        populate_by_name = True


class DeviceRegistration(BaseModel):
    """Device trust model for zero-trust architecture."""
    device_id: str
    user_id: str
    device_type: str  # "phone", "laptop", "tablet"
    os: str  # "ios", "android", "macos", "windows", "linux"
    certificate_fingerprint: str  # Hardware certificate
    certificate_expiry: datetime
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime
    geofence_exceptions: List[str] = []  # Geofence IDs where device is pre-approved
    metadata: Dict[str, Any] = {}

    @field_validator('certificate_expiry')
    def validate_expiry(cls, v):
        if v < datetime.now(timezone.utc):
            raise ValueError("Certificate cannot be expired")
        return v


class SessionState(BaseModel):
    """Active WebSocket/HTTP session."""
    session_id: str
    user_id: str
    device_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    is_valid: bool = True
    # Multi-modal validation history
    device_verified_at: Optional[datetime] = None
    biometric_verified_at: Optional[datetime] = None
    spatial_verified_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


# ============================================================================
# VENUE / ROOM MODELS
# ============================================================================

class GeoJSONPoint(BaseModel):
    """GeoJSON Point for spatial queries."""
    type: str = "Point"
    coordinates: List[float]  # [lng, lat]

    @field_validator('coordinates')
    def validate_coords(cls, v):
        if len(v) != 2:
            raise ValueError("coordinates must be [longitude, latitude]")
        lng, lat = v
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            raise ValueError("Invalid longitude/latitude")
        return v


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon for geofence boundaries."""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]  # [[[lng, lat], [lng, lat], ...]]


class GeofenceDefinition(BaseModel):
    """Geofence (building or room boundary)."""
    geofence_id: str
    name: str
    campus_location: str  # e.g., "Building A, Room 101"
    boundary: GeoJSONPolygon
    # Beacon/network environment
    expected_bssids: List[str] = []  # WiFi APs
    bluetooth_beacons: List[str] = []  # iBeacon UUIDs
    # Permissions
    allowed_roles: List[RoleEnum] = [RoleEnum.student, RoleEnum.faculty]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = {}


class RoomOccupancy(BaseModel):
    """Real-time occupancy sensor data."""
    room_id: str
    current_occupancy: int
    capacity: int
    last_updated: datetime
    sensor_reliability: float  # 0.0-1.0 confidence


# ============================================================================
# CURRICULUM MODELS (Mutable state)
# ============================================================================

class LearningOutcome(BaseModel):
    """Learning outcome for a course."""
    outcome_id: str
    course_id: str
    title: str
    description: str
    level: str  # "foundational", "intermediate", "advanced"
    assessment_type: str  # "exam", "project", "participation"


class CurriculumNode(BaseModel):
    """DAG node in curriculum knowledge graph."""
    node_id: str
    course_id: str
    title: str
    node_type: str  # "module", "topic", "lesson"
    learning_outcomes: List[str]  # References to LearningOutcome IDs
    prerequisites: List[str] = []  # Parent node IDs
    resource_uris: List[str] = []  # PDFs, videos
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = {}


class CourseDefinition(BaseModel):
    """Course metadata (mutable)."""
    course_id: str
    course_code: str  # e.g., "MATH-101"
    title: str
    faculty_id: str
    enrollment_count: int
    curriculum_root_nodes: List[str]  # Root node IDs in curriculum DAG
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = {}


# ============================================================================
# IMMUTABLE EVENT MODELS (Append-only collections)
# ============================================================================

class AttendanceEventSignals(BaseModel):
    """Multi-modal validation signals for attendance."""
    device_valid: bool
    device_id: str
    biometric_valid: bool
    biometric_confidence: float  # 0.0-1.0
    spatial_valid: bool
    geofence_distance_meters: float
    network_environment_valid: Optional[bool] = None


class AttendanceEvent(BaseModel):
    """Immutable attendance log entry."""
    event_id: str = Field(default_factory=lambda: str(ObjectId()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    course_id: str
    geofence_id: str
    session_id: str
    # Multi-modal signals
    signals: AttendanceEventSignals
    # Outcome
    status: str  # "marked", "pending_override", "denied"
    is_spoofed: bool = False
    # Audit trail
    actor: str  # user_id or "system"
    metadata: Dict[str, Any] = {}


class CurriculumEventData(BaseModel):
    """Curriculum extraction from audio/syllabus."""
    concept: str
    source: str  # "audio_transcript", "syllabus_pdf", "faculty_manual"
    confidence: float  # 0.0-1.0
    learning_outcome_id: Optional[str] = None
    instructor_correction: Optional[str] = None


class CurriculumEvent(BaseModel):
    """Immutable curriculum mapping event."""
    event_id: str = Field(default_factory=lambda: str(ObjectId()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str
    course_id: str
    # Extracted concepts
    concepts: List[CurriculumEventData]
    # Inference lineage
    inference_model: str  # "ollama-llama2-v1.3"
    inference_version: str
    inference_prompt_version: str
    # Audit
    actor: str
    metadata: Dict[str, Any] = {}


class RiskEventData(BaseModel):
    """Risk factor for student."""
    factor_name: str  # "high_absence_rate", "low_engagement", "biometric_anomaly"
    factor_value: float
    contribution_to_score: float
    metadata: Dict[str, Any] = {}


class RiskEvent(BaseModel):
    """Immutable risk assessment event."""
    event_id: str = Field(default_factory=lambda: str(ObjectId()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    course_id: str
    # Risk calculation
    risk_score: float  # 0.0-1.0
    risk_level: str  # "low", "medium", "high", "critical"
    contributing_factors: List[RiskEventData]
    # ML model info
    model_name: str
    model_version: str
    formula_version: str
    # SHAP explanation
    shap_values: Dict[str, float]
    # Audit
    actor: str
    metadata: Dict[str, Any] = {}


class OverrideEvent(BaseModel):
    """Immutable override audit trail."""
    event_id: str = Field(default_factory=lambda: str(ObjectId()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # What was overridden
    entity_type: str  # "attendance", "risk_flag"
    entity_id: str
    old_state: Dict[str, Any]
    new_state: Dict[str, Any]
    # Who and why
    actor: str  # faculty_id or admin_id
    reason: str
    actor_biometric_verified: bool  # Faculty must re-verify
    # Signature
    actor_signature: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ============================================================================
# AUDIT LOG MODEL (Immutable, tamper-evident)
# ============================================================================

class AuditLogEntry(BaseModel):
    """Immutable, signed audit log entry."""
    log_id: str = Field(default_factory=lambda: str(ObjectId()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Request context
    request_id: str
    actor: str  # user_id or "system"
    actor_role: RoleEnum
    action: str  # "create", "read", "update", "delete", "override"
    # Target
    resource_type: str  # "user", "attendance", "risk_score"
    resource_id: str
    # Changes
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    # Tamper-evidence
    previous_log_hash: Optional[str] = None  # SHA256 of previous entry
    signature: Optional[str] = None  # RSA-signed by admin
    # Status
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ============================================================================
# API RESPONSE MODELS
# ============================================================================

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    status: str  # "success", "error"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValidationError(BaseModel):
    """Structured validation error response."""
    field: str
    message: str
    value: Optional[Any] = None
