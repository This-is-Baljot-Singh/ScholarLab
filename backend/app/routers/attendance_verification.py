"""
Attendance verification router: Orchestrates zero-trust multi-signal gates.

Endpoints:
- POST /sessions - Create attendance session (faculty)
- POST /sessions/{session_id}/nonce - Request nonce (student)
- POST /checkin - Verify attendance (ALL 6 gates)
- GET /sessions/{session_id}/stats - Session statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.security import get_current_user
from app.logging.audit import AuditLogger, set_actor

from app.contexts.attendance import (
    DeviceRegistrationService,
    BiometricLivenessService,
    SpatialFusionEngine,
    AttendanceDecisionEngine,
    SessionNonceManager,
)
from app.contexts.attendance.decision_engine import (
    AttendanceCheckInRequest,
    AttendanceCheckInResponse,
)
from app.contexts.attendance.session_manager import (
    CreateSessionRequest,
    CreateSessionResponse,
    RequestNonceRequest,
    RequestNonceResponse,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


# ============================================================================
# SESSION ENDPOINTS (FACULTY)
# ============================================================================

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_attendance_session(
    request: CreateSessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Faculty creates attendance session.
    
    Opens check-in window for students to verify attendance.
    """
    actor = current_user.get("user_id")
    await set_actor(actor)
    
    # Verify faculty role
    if current_user.get("role") != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can create sessions")
    
    # Initialize services
    session_manager = SessionNonceManager(db)
    await session_manager.initialize()
    
    # Create session
    session = await session_manager.create_session(
        course_id=request.course_id,
        faculty_id=actor,
        geofence_id=request.geofence_id,
        lecture_title=request.lecture_title,
        duration_minutes=request.duration_minutes,
        expected_students=request.expected_students,
    )
    
    # Audit
    audit_logger = AuditLogger(db)
    await audit_logger.log(
        action="session_created",
        resource_type="attendance_session",
        resource_id=session.session_id,
        actor=actor,
        details={
            "course_id": request.course_id,
            "geofence_id": request.geofence_id,
            "expected_students": request.expected_students,
        }
    )
    
    return CreateSessionResponse(
        session_id=session.session_id,
        started_at=session.started_at,
        expires_at=session.expires_at,
        expected_duration_minutes=session.expected_duration_minutes,
    )


@router.get("/sessions/{session_id}/stats")
async def get_session_statistics(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Faculty reviews session attendance statistics.
    """
    actor = current_user.get("user_id")
    
    # Initialize services
    session_manager = SessionNonceManager(db)
    await session_manager.initialize()
    
    # Verify faculty owns session
    session = await session_manager.get_session(session_id)
    if not session or session.faculty_id != actor:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get stats
    stats = await session_manager.get_session_statistics(session_id)
    
    return stats


# ============================================================================
# NONCE ENDPOINTS (STUDENT)
# ============================================================================

@router.post("/sessions/{session_id}/nonce", response_model=RequestNonceResponse)
async def request_nonce(
    session_id: str,
    request: RequestNonceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Student requests nonce for check-in.
    
    Nonce is short-lived (5 minutes) and bound to:
    - Session
    - Student
    - Device
    
    Prevents replay attacks.
    """
    user_id = current_user.get("user_id")
    device_id = request.device_id
    
    await set_actor(user_id)
    
    # Initialize services
    session_manager = SessionNonceManager(db)
    await session_manager.initialize()
    
    # Verify session active
    if not await session_manager.is_session_active(session_id):
        raise HTTPException(status_code=410, detail="Session not active")
    
    # Check rate limit
    if not await session_manager.check_nonce_rate_limit(user_id, device_id):
        raise HTTPException(status_code=429, detail="Too many nonce requests")
    
    # Create nonce
    try:
        nonce_record = await session_manager.create_nonce(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            validity_seconds=300,  # 5 minutes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Audit
    audit_logger = AuditLogger(db)
    await audit_logger.log(
        action="nonce_requested",
        resource_type="session_nonce",
        resource_id=session_id,
        actor=user_id,
        details={"device_id": device_id}
    )
    
    return RequestNonceResponse(
        nonce=nonce_record.nonce,
        expires_in_seconds=300,
        session_id=session_id,
    )


# ============================================================================
# CHECK-IN ENDPOINT (ORCHESTRATE ALL 6 GATES)
# ============================================================================

@router.post("/checkin", response_model=AttendanceCheckInResponse)
async def verify_attendance(
    request: AttendanceCheckInRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Student checks in: Orchestrate all 6 verification gates.
    
    Decision Rule: A_t = G_t AND K_t AND M_t AND N_t AND B_t AND D_t
    
    Where:
    - G_t = Geofence signal valid (C_t >= 0.70)
    - K_t = Cryptographic signature verified
    - M_t = Multi-modal validation passed
    - N_t = Nonce valid (not expired, not replayed)
    - B_t = Biometric liveness gate passed
    - D_t = Device registered and trusted
    
    ALL 6 MUST BE TRUE for attendance to be marked.
    """
    user_id = current_user.get("user_id")
    
    await set_actor(user_id)
    
    # Initialize all services
    device_service = DeviceRegistrationService(db)
    biometric_service = BiometricLivenessService(db)
    spatial_engine = SpatialFusionEngine(db)
    decision_engine = AttendanceDecisionEngine(db)
    session_manager = SessionNonceManager(db)
    
    await device_service.initialize()
    await biometric_service.initialize()
    await spatial_engine.initialize()
    await decision_engine.initialize()
    await session_manager.initialize()
    
    # Verify session active
    if not await session_manager.is_session_active(request.session_id):
        raise HTTPException(status_code=410, detail="Session not active")
    
    # ===== GATE 1: Device verification (D_t) =====
    try:
        device_verified = await device_service.verify_device_signature(
            device_id=request.device_id,
            signature_data=request.device_signature,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Device verification failed: {str(e)}")
    
    # ===== GATE 2: Nonce validation (N_t) =====
    try:
        await session_manager.validate_nonce(
            nonce=request.nonce,
            session_id=request.session_id,
            user_id=user_id,
            device_id=request.device_id,
        )
        nonce_valid = True
    except ValueError as e:
        nonce_valid = False
    
    # ===== GATE 3: Biometric verification (B_t) =====
    try:
        biometric_verified = await biometric_service.is_verification_valid(
            session_id=request.session_id,
            modality="face",  # or fingerprint, iris, etc.
        )
    except Exception:
        biometric_verified = False
    
    # ===== GATE 4: Spatial fusion (G_t + location signals) =====
    try:
        spatial_result = await spatial_engine.compute_composite_confidence(
            session_id=request.session_id,
            user_id=user_id,
            geofence_id=request.geofence_id,
            latitude=request.latitude,
            longitude=request.longitude,
            observed_beacons=request.observed_beacons,
            floor=request.floor,
            magnetic_field_vector=tuple(request.magnetic_field) if request.magnetic_field else None,
        )
        geofence_score = spatial_result.composite_confidence
        spatial_verified = spatial_result.confidence_level in ["high", "medium"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Spatial verification failed: {str(e)}")
    
    # ===== ORCHESTRATE ALL 6 GATES =====
    try:
        decision = await decision_engine.evaluate_attendance(
            user_id=user_id,
            device_id=request.device_id,
            session_id=request.session_id,
            course_id=request.course_id,
            geofence_id=request.geofence_id,
            # Gate inputs
            geofence_score=geofence_score,
            signature_valid=device_verified,
            signature_data=request.device_signature,
            device_verified=device_verified,
            biometric_verified=biometric_verified,
            spatial_verified=spatial_verified,
            nonce=request.nonce,
            biometric_outcome=request.biometric_outcome,
            biometric_confidence=request.biometric_confidence,
            liveness_score=request.liveness_score,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision pipeline error: {str(e)}")
    
    # ===== AUDIT & RESPONSE =====
    audit_logger = AuditLogger(db)
    
    gates_passed = sum(1 for gate in decision.gates.values() if gate["passed"])
    
    await audit_logger.log(
        action="attendance_verification",
        resource_type="attendance_decision",
        resource_id=decision.decision_id,
        actor=user_id,
        details={
            "session_id": request.session_id,
            "course_id": request.course_id,
            "decision": "approved" if decision.attendance_marked else "denied",
            "gates_passed": gates_passed,
            "failed_gates": decision.failed_gates,
        }
    )
    
    return AttendanceCheckInResponse(
        decision_id=decision.decision_id,
        attendance_marked=decision.attendance_marked,
        reasoning=decision.decision_reasoning,
        gates_passed=gates_passed,
        gates_failed=decision.failed_gates,
        timestamp=decision.timestamp,
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@router.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return {
        "detail": str(exc),
        "error_code": "validation_error",
    }
