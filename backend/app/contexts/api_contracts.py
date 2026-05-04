"""
Strict API request/response contracts with Pydantic validation.

Each bounded context defines its own request/response models.
Input: Strict validation with min/max lengths, regex, ranges.
Output: Typed responses with audit trail references.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


# ============================================================================
# AUTH CONTEXT API CONTRACTS
# ============================================================================

class LoginRequest(BaseModel):
    """Strict login request validation."""
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password must be 8-128 chars"
    )

    @field_validator('password')
    def validate_password(cls, v):
        """Ensure password meets complexity requirements."""
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*" for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password must contain uppercase, lowercase, and digit")
        return v


class UserCreateRequest(BaseModel):
    """Strict user creation request."""
    email: EmailStr
    full_name: str = Field(
        min_length=2,
        max_length=256,
        description="Full name, 2-256 chars"
    )
    role: str = Field(
        pattern="^(student|faculty|admin)$",
        description="Must be student, faculty, or admin"
    )
    password: str = Field(
        min_length=8,
        max_length=128
    )

    @field_validator('full_name')
    def validate_full_name(cls, v):
        if not v.replace(" ", "").isalpha():
            raise ValueError("Full name must contain only letters and spaces")
        return v


class LoginResponse(BaseModel):
    """Login response with audit reference."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: Dict[str, Any]  # {id, email, role, full_name}
    audit_log_id: str  # Reference for compliance


class WebAuthnOptionsRequest(BaseModel):
    """Request WebAuthn challenge."""
    email: EmailStr


class WebAuthnOptionsResponse(BaseModel):
    """WebAuthn challenge for biometric registration/auth."""
    challenge: str
    rp_id: str
    origin: str
    user_id: str
    user_name: str
    user_display_name: str


class WebAuthnRegistrationVerifyRequest(BaseModel):
    """Verify WebAuthn registration."""
    email: EmailStr
    credential: Dict[str, Any] = Field(
        description="Credential from @simplewebauthn/browser"
    )

    @field_validator('credential')
    def validate_credential(cls, v):
        required_fields = ['id', 'rawId', 'response', 'type']
        if not all(field in v for field in required_fields):
            raise ValueError(f"Credential must contain: {required_fields}")
        return v


class WebAuthnAuthVerifyRequest(BaseModel):
    """Verify WebAuthn authentication."""
    email: EmailStr
    credential: Dict[str, Any] = Field(
        description="Credential from @simplewebauthn/browser"
    )


# ============================================================================
# ATTENDANCE CONTEXT API CONTRACTS
# ============================================================================

class AttendanceVerifyRequest(BaseModel):
    """Strict attendance verification request (zero-trust multi-modal)."""
    session_id: str = Field(
        min_length=16,
        max_length=64,
        description="WebSocket session ID"
    )
    course_id: str = Field(
        min_length=1,
        max_length=64
    )
    geofence_id: str = Field(
        min_length=1,
        max_length=64
    )
    latitude: float = Field(
        ge=-90,
        le=90,
        description="Latitude -90 to 90"
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        description="Longitude -180 to 180"
    )
    # Device signal
    device_id: str = Field(
        min_length=1,
        max_length=256
    )
    device_certificate_fingerprint: str = Field(
        regex="^[a-f0-9]{64}$",
        description="SHA256 hex fingerprint"
    )
    # Biometric signal
    biometric_credential: Dict[str, Any] = Field(
        description="WebAuthn credential from client"
    )
    # Network environment
    bssid: Optional[str] = Field(
        None,
        regex="^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
        description="WiFi MAC address (optional)"
    )

    @field_validator('biometric_credential')
    def validate_biometric(cls, v):
        required = ['id', 'rawId', 'response']
        if not all(k in v for k in required):
            raise ValueError("biometric_credential must have id, rawId, response")
        return v

    @model_validator(mode='after')
    def validate_location_precision(self):
        """Ensure location has reasonable precision (5 decimal places = ~1m)."""
        lat_precision = len(str(self.latitude).split('.')[-1])
        lng_precision = len(str(self.longitude).split('.')[-1])
        if lat_precision < 4 or lng_precision < 4:
            raise ValueError("Latitude/longitude must have at least 4 decimal places")
        return self


class AttendanceVerifyResponse(BaseModel):
    """Attendance verification response."""
    status: str  # "marked", "pending_override", "denied"
    message: str
    attendance_event_id: str
    timestamp: datetime
    signals_validated: Dict[str, bool]  # {device, biometric, spatial}
    risk_score: Optional[float] = None
    audit_log_id: str


class AttendanceHistoryRequest(BaseModel):
    """Request attendance history."""
    course_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Max 1000 records per request"
    )


class AttendanceRecord(BaseModel):
    """Single attendance record in history."""
    event_id: str
    timestamp: datetime
    course_id: str
    status: str
    signals: Dict[str, Any]
    is_spoofed: bool


class AttendanceHistoryResponse(BaseModel):
    """Attendance history response."""
    records: List[AttendanceRecord]
    total_count: int
    page: int


# ============================================================================
# CURRICULUM CONTEXT API CONTRACTS
# ============================================================================

class CurriculumNodeCreateRequest(BaseModel):
    """Create curriculum node."""
    course_id: str = Field(
        min_length=1,
        max_length=64
    )
    title: str = Field(
        min_length=1,
        max_length=512
    )
    node_type: str = Field(
        pattern="^(module|topic|lesson)$"
    )
    learning_outcomes: List[str] = Field(
        max_length=20,
        description="Max 20 learning outcomes per node"
    )
    prerequisites: List[str] = Field(
        default=[],
        max_length=10,
        description="Max 10 prerequisites"
    )
    resource_uris: List[str] = Field(
        default=[],
        max_length=50
    )

    @field_validator('resource_uris')
    def validate_uris(cls, v):
        for uri in v:
            if not uri.startswith(('http://', 'https://', 'file://')):
                raise ValueError("Resource URIs must be absolute URLs or file:// paths")
        return v


class CurriculumNodeResponse(BaseModel):
    """Curriculum node in response."""
    node_id: str
    course_id: str
    title: str
    node_type: str
    learning_outcomes: List[str]
    prerequisites: List[str]
    resource_uris: List[str]


# ============================================================================
# ANALYTICS CONTEXT API CONTRACTS
# ============================================================================

class RiskScoreRequest(BaseModel):
    """Request risk score calculation."""
    user_id: str
    course_id: str
    lookback_days: int = Field(
        default=30,
        ge=7,
        le=365,
        description="Lookback window 7-365 days"
    )


class RiskScoreResponse(BaseModel):
    """Risk score with explainability."""
    risk_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Risk 0.0-1.0"
    )
    risk_level: str  # "low", "medium", "high", "critical"
    model_version: str
    formula_version: str
    contributing_factors: List[Dict[str, Any]]  # {name, value, contribution}
    shap_values: Dict[str, float]  # Feature importance
    risk_event_id: str  # Immutable event reference
    generated_at: datetime


class AnalyticsAggregateRequest(BaseModel):
    """Request aggregate analytics."""
    course_id: str
    metric: str = Field(
        pattern="^(attendance_rate|avg_risk|engagement_score)$"
    )
    group_by: Optional[str] = Field(
        None,
        pattern="^(day|week|month)$"
    )
    start_date: datetime
    end_date: datetime

    @model_validator(mode='after')
    def validate_date_range(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


# ============================================================================
# EVENTS/WEBSOCKETS CONTEXT API CONTRACTS
# ============================================================================

class WebSocketMessageRequest(BaseModel):
    """Validated WebSocket message."""
    message_type: str = Field(
        pattern="^(attendance_check_in|curriculum_update|risk_alert|override_request)$"
    )
    payload: Dict[str, Any] = Field(
        description="Type-specific payload"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# AUDIT CONTEXT API CONTRACTS
# ============================================================================

class AuditLogQueryRequest(BaseModel):
    """Query audit logs."""
    actor_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    start_date: datetime
    end_date: datetime
    limit: int = Field(
        default=100,
        ge=1,
        le=10000
    )

    @model_validator(mode='after')
    def validate_date_range(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class AuditLogEntry(BaseModel):
    """Audit log entry in response."""
    log_id: str
    timestamp: datetime
    actor: str
    action: str
    resource_type: str
    resource_id: str
    success: bool
    error_message: Optional[str] = None
    signature: Optional[str] = None


class AuditLogQueryResponse(BaseModel):
    """Audit log query response."""
    logs: List[AuditLogEntry]
    total_count: int
    query_executed_at: datetime


# ============================================================================
# ERROR RESPONSE CONTRACTS
# ============================================================================

class ErrorDetail(BaseModel):
    """Structured error detail."""
    field: Optional[str] = None
    message: str
    error_code: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = "error"
    error_code: str
    message: str
    details: List[ErrorDetail] = []
    request_id: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
