"""
Hard-Gate Attendance Decision Pipeline.

Decision Rule:
A_t = G_t AND K_t AND M_t AND N_t AND B_t AND D_t

Where:
- G_t = Geofence signal valid (C_t >= 0.70)
- K_t = Cryptographic signature verified
- M_t = Multi-modal validation passed (all 3: device + biometric + spatial)
- N_t = Nonce valid (not expired, not replayed)
- B_t = Biometric liveness gate passed (confidence >= 0.95, liveness >= 0.80)
- D_t = Device registered and trusted (not cloned, cert valid)

ALL 6 MUST BE TRUE for A_t = True

Decision is immutable once made. Logged to audit trail.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class AttendanceGate(str, Enum):
    """Individual gate in the hard-gate pipeline."""
    GEOFENCE = "geofence"  # G_t
    CRYPTOGRAPHIC = "cryptographic"  # K_t
    MULTIMODAL = "multimodal"  # M_t
    NONCE = "nonce"  # N_t
    BIOMETRIC = "biometric"  # B_t
    DEVICE = "device"  # D_t


class GateResult(BaseModel):
    """Result of a single gate check."""
    gate: AttendanceGate
    passed: bool
    confidence: float = 0.0  # 0.0-1.0
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AttendanceDecision(BaseModel):
    """Final attendance decision (immutable)."""
    decision_id: str
    user_id: str
    device_id: str
    session_id: str
    course_id: str
    geofence_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Gate results
    gates: Dict[str, GateResult]  # {gate_name: result}
    # Final decision
    attendance_marked: bool  # A_t = G_t AND K_t AND M_t AND N_t AND B_t AND D_t
    decision_reasoning: str  # Why marked or rejected
    # Audit
    all_gates_passed: bool = False
    any_gate_failed: bool = False
    failed_gates: list = []


# ============================================================================
# HARD-GATE DECISION ENGINE
# ============================================================================

class AttendanceDecisionEngine:
    """
    Evaluates all 6 gates and makes final attendance decision.
    
    Principle: ALL gates must pass (hard AND gate).
    No single strong signal can override weak signals.
    
    Decision is immutable once made and stored.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.attendance_decisions_col: AsyncIOMotorCollection = db["attendance_decisions"]
        self.gate_audit_col: AsyncIOMotorCollection = db["gate_audit_logs"]
    
    async def initialize(self):
        """Setup decision collection indexes."""
        await self.attendance_decisions_col.create_index("decision_id", unique=True)
        await self.attendance_decisions_col.create_index("session_id", unique=True)
        await self.attendance_decisions_col.create_index("user_id")
        await self.attendance_decisions_col.create_index("course_id")
        # Gate audit trail
        await self.gate_audit_col.create_index("decision_id")
        await self.gate_audit_col.create_index("timestamp")
        logger.info("Attendance decision engine initialized")
    
    # ========================================================================
    # INDIVIDUAL GATE CHECKS
    # ========================================================================
    
    async def check_geofence_gate(
        self,
        geofence_score: float,
    ) -> GateResult:
        """
        G_t: Geofence validity gate.
        
        Requires: Composite confidence score >= 0.70
        
        Args:
            geofence_score: Composite spatial fusion score (C_t)
        
        Returns:
            GateResult with pass/fail
        """
        threshold = 0.70
        passed = geofence_score >= threshold
        
        return GateResult(
            gate=AttendanceGate.GEOFENCE,
            passed=passed,
            confidence=geofence_score,
            reason=f"Spatial confidence {geofence_score:.2f} {'≥' if passed else '<'} {threshold}",
        )
    
    async def check_cryptographic_gate(
        self,
        device_id: str,
        signature_valid: bool,
        signature_data: Dict[str, Any],
    ) -> GateResult:
        """
        K_t: Cryptographic signature verification gate.
        
        Requires: Device signature valid (signed with device's private key)
        
        Args:
            device_id: Device ID
            signature_valid: Was signature verification successful?
            signature_data: Data that was signed
        
        Returns:
            GateResult with pass/fail
        """
        device_service = await self._get_device_service()
        
        # Verify device exists and is trusted
        device = await device_service.get_device(device_id)
        if not device:
            return GateResult(
                gate=AttendanceGate.CRYPTOGRAPHIC,
                passed=False,
                reason="Device not found",
            )
        
        # Check certificate expiry
        from datetime import timezone
        if device.certificate_expiry <= datetime.now(timezone.utc):
            return GateResult(
                gate=AttendanceGate.CRYPTOGRAPHIC,
                passed=False,
                reason="Device certificate expired",
            )
        
        # Verify signature
        passed = signature_valid and device.is_trusted
        
        return GateResult(
            gate=AttendanceGate.CRYPTOGRAPHIC,
            passed=passed,
            confidence=1.0 if passed else 0.0,
            reason="Valid signature" if passed else "Invalid signature or untrusted device",
        )
    
    async def check_multimodal_gate(
        self,
        device_verified: bool,
        biometric_verified: bool,
        spatial_verified: bool,
    ) -> GateResult:
        """
        M_t: Multi-modal validation gate.
        
        Requires: ALL THREE signals verified
        - Device: Registered, trusted, certificate valid
        - Biometric: Liveness passed, confidence >= 0.95
        - Spatial: Composite confidence >= 0.70
        
        Args:
            device_verified: Device gate passed?
            biometric_verified: Biometric gate passed?
            spatial_verified: Spatial gate passed?
        
        Returns:
            GateResult with pass/fail
        """
        all_verified = device_verified and biometric_verified and spatial_verified
        verified_count = sum([device_verified, biometric_verified, spatial_verified])
        
        return GateResult(
            gate=AttendanceGate.MULTIMODAL,
            passed=all_verified,
            confidence=verified_count / 3.0,
            reason=f"{verified_count}/3 modalities verified" + 
                   (" ✓ ALL PASS" if all_verified else " ✗ INCOMPLETE"),
        )
    
    async def check_nonce_gate(
        self,
        nonce: str,
        session_id: str,
        user_id: str,
        device_id: str,
    ) -> GateResult:
        """
        N_t: Nonce validity gate (replay protection).
        
        Requires:
        - Nonce exists
        - Nonce not expired
        - Nonce not previously used
        - Nonce bindings match (user, device, session)
        
        Args:
            nonce: Cryptographic nonce to verify
            session_id, user_id, device_id: Binding values
        
        Returns:
            GateResult with pass/fail
        """
        try:
            # This will raise ValueError if nonce is invalid
            biometric_service = await self._get_biometric_service()
            await biometric_service.verify_nonce(nonce, user_id, device_id, session_id)
            
            return GateResult(
                gate=AttendanceGate.NONCE,
                passed=True,
                confidence=1.0,
                reason="Nonce valid and fresh",
            )
        except ValueError as e:
            return GateResult(
                gate=AttendanceGate.NONCE,
                passed=False,
                confidence=0.0,
                reason=f"Nonce invalid: {str(e)}",
            )
    
    async def check_biometric_gate(
        self,
        biometric_outcome: str,  # "pass", "fail", "inconclusive"
        biometric_confidence: float,
        liveness_score: float,
    ) -> GateResult:
        """
        B_t: Biometric liveness gate.
        
        Requires:
        - Outcome: "pass"
        - Confidence >= 0.95
        - Liveness score >= 0.80
        - Anti-spoofing checks passed
        
        Args:
            biometric_outcome: pass/fail/inconclusive
            biometric_confidence: Match confidence (0.0-1.0)
            liveness_score: Liveness score (0.0-1.0)
        
        Returns:
            GateResult with pass/fail
        """
        MIN_CONFIDENCE = 0.95
        MIN_LIVENESS = 0.80
        
        outcome_pass = biometric_outcome == "pass"
        confidence_ok = biometric_confidence >= MIN_CONFIDENCE
        liveness_ok = liveness_score >= MIN_LIVENESS
        
        all_pass = outcome_pass and confidence_ok and liveness_ok
        
        reason_parts = []
        if not outcome_pass:
            reason_parts.append(f"outcome={biometric_outcome}")
        if not confidence_ok:
            reason_parts.append(f"confidence={biometric_confidence:.2f}<{MIN_CONFIDENCE}")
        if not liveness_ok:
            reason_parts.append(f"liveness={liveness_score:.2f}<{MIN_LIVENESS}")
        
        return GateResult(
            gate=AttendanceGate.BIOMETRIC,
            passed=all_pass,
            confidence=biometric_confidence,
            reason=" AND ".join(reason_parts) if reason_parts else "Biometric verified",
        )
    
    async def check_device_gate(
        self,
        device_id: str,
    ) -> GateResult:
        """
        D_t: Device trust gate.
        
        Requires:
        - Device registered
        - Device trusted (not cloned)
        - Certificate valid
        - No excessive failed auth attempts
        
        Args:
            device_id: Device ID to check
        
        Returns:
            GateResult with pass/fail
        """
        device_service = await self._get_device_service()
        
        try:
            device = await device_service.get_device(device_id)
            if not device:
                return GateResult(
                    gate=AttendanceGate.DEVICE,
                    passed=False,
                    reason="Device not registered",
                )
            
            # Check trust status
            if not device.is_trusted:
                return GateResult(
                    gate=AttendanceGate.DEVICE,
                    passed=False,
                    reason="Device not approved (pending admin review)",
                )
            
            # Check certificate
            if device.certificate_expiry <= datetime.now(timezone.utc):
                return GateResult(
                    gate=AttendanceGate.DEVICE,
                    passed=False,
                    reason="Device certificate expired",
                )
            
            # Check for cloning attacks
            if device.failed_verification_count > 10:
                return GateResult(
                    gate=AttendanceGate.DEVICE,
                    passed=False,
                    reason="Device has excessive failures (possible compromise)",
                )
            
            return GateResult(
                gate=AttendanceGate.DEVICE,
                passed=True,
                confidence=1.0,
                reason="Device registered and trusted",
            )
        except Exception as e:
            logger.error(f"Device gate check failed: {e}")
            return GateResult(
                gate=AttendanceGate.DEVICE,
                passed=False,
                reason=f"Error: {str(e)}",
            )
    
    # ========================================================================
    # FINAL DECISION
    # ========================================================================
    
    async def evaluate_attendance(
        self,
        user_id: str,
        device_id: str,
        session_id: str,
        course_id: str,
        geofence_id: str,
        # Gate inputs
        geofence_score: float,
        signature_valid: bool,
        signature_data: Dict[str, Any],
        device_verified: bool,
        biometric_verified: bool,
        spatial_verified: bool,
        nonce: str,
        biometric_outcome: str,
        biometric_confidence: float,
        liveness_score: float,
    ) -> AttendanceDecision:
        """
        Evaluate all 6 gates and make final attendance decision.
        
        Decision Rule: A_t = G_t AND K_t AND M_t AND N_t AND B_t AND D_t
        
        ALL 6 must be True for attendance to be marked.
        
        Args:
            All gate input parameters
        
        Returns:
            AttendanceDecision (immutable)
        """
        # Check each gate
        gates = {}
        
        gates["geofence"] = await self.check_geofence_gate(geofence_score)
        gates["cryptographic"] = await self.check_cryptographic_gate(device_id, signature_valid, signature_data)
        gates["multimodal"] = await self.check_multimodal_gate(device_verified, biometric_verified, spatial_verified)
        gates["nonce"] = await self.check_nonce_gate(nonce, session_id, user_id, device_id)
        gates["biometric"] = await self.check_biometric_gate(biometric_outcome, biometric_confidence, liveness_score)
        gates["device"] = await self.check_device_gate(device_id)
        
        # Hard AND gate: ALL must pass
        all_gates_passed = all(gate.passed for gate in gates.values())
        failed_gates = [name for name, gate in gates.items() if not gate.passed]
        
        # Build reasoning
        if all_gates_passed:
            decision_reasoning = "✓ ALL GATES PASSED: Attendance marked"
        else:
            decision_reasoning = f"✗ REJECTED: Failed gates: {', '.join(failed_gates)}"
        
        # Create immutable decision
        decision_id = str(ObjectId())
        decision = AttendanceDecision(
            decision_id=decision_id,
            user_id=user_id,
            device_id=device_id,
            session_id=session_id,
            course_id=course_id,
            geofence_id=geofence_id,
            timestamp=datetime.now(timezone.utc),
            gates={name: gate.dict() for name, gate in gates.items()},
            attendance_marked=all_gates_passed,
            decision_reasoning=decision_reasoning,
            all_gates_passed=all_gates_passed,
            any_gate_failed=len(failed_gates) > 0,
            failed_gates=failed_gates,
        )
        
        # Store immutable decision
        doc = decision.dict()
        doc["_id"] = ObjectId()
        await self.attendance_decisions_col.insert_one(doc)
        
        # Log gate audit trail
        for gate_name, gate_result in gates.items():
            await self.gate_audit_col.insert_one({
                "decision_id": decision_id,
                "gate": gate_name,
                "passed": gate_result.passed,
                "confidence": gate_result.confidence,
                "reason": gate_result.reason,
                "timestamp": gate_result.timestamp,
            })
        
        # Log final decision
        logger.info(
            f"Attendance decision: {decision_reasoning}",
            extra={
                "decision_id": decision_id,
                "user_id": user_id,
                "session_id": session_id,
                "attendance_marked": all_gates_passed,
                "gates": {name: gate["passed"] for name, gate in decision.gates.items()},
            }
        )
        
        return decision
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    async def _get_device_service(self):
        """Lazy-load device service."""
        from app.contexts.attendance.device_registration import DeviceRegistrationService
        return DeviceRegistrationService(self.db)
    
    async def _get_biometric_service(self):
        """Lazy-load biometric service."""
        from app.contexts.attendance.biometric_liveness import BiometricLivenessService
        return BiometricLivenessService(self.db)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AttendanceCheckInRequest(BaseModel):
    """Student check-in request (all 6 gates worth of data)."""
    session_id: str
    course_id: str
    geofence_id: str
    # Location
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    # Device
    device_id: str
    device_signature: Dict[str, Any]  # Signed by device
    # Biometric
    nonce: str
    biometric_outcome: str  # "pass", "fail"
    biometric_confidence: float = Field(ge=0.0, le=1.0)
    liveness_score: float = Field(ge=0.0, le=1.0)
    # Spatial
    observed_beacons: list = []
    floor: Optional[int] = None
    magnetic_field: Optional[list] = None  # [x, y, z]


class AttendanceCheckInResponse(BaseModel):
    """Check-in response."""
    decision_id: str
    attendance_marked: bool
    reasoning: str
    gates_passed: int  # How many of 6 gates passed?
    gates_failed: list  # Which gates failed?
    timestamp: datetime
