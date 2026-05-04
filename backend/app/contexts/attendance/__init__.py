"""
Attendance verification context: Zero-trust multi-signal gates.

Services:
- DeviceRegistrationService: Device binding, signature verification, clone detection
- BiometricLivenessService: Biometric verification, nonce-based replay protection
- SpatialFusionEngine: Multi-signal location confidence (6 signals)
- AttendanceDecisionEngine: Hard-gate conjunction (ALL 6 must pass)
- SessionNonceManager: Session lifecycle, nonce management
"""

from .device_registration import (
    DeviceRegistrationService,
    DeviceBinding,
    WebAuthnCredential,
)
from .biometric_liveness import (
    BiometricLivenessService,
    BiometricVerificationRecord,
    LivenessCheckOutcome,
)
from .spatial_fusion import (
    SpatialFusionEngine,
    SpatialFusionResult,
)
from .decision_engine import (
    AttendanceDecisionEngine,
    AttendanceDecision,
    AttendanceGate,
    GateResult,
)
from .session_manager import (
    SessionNonceManager,
    AttendanceSession,
    SessionNonce,
)

__all__ = [
    # Device Registration
    "DeviceRegistrationService",
    "DeviceBinding",
    "WebAuthnCredential",
    # Biometric Liveness
    "BiometricLivenessService",
    "BiometricVerificationRecord",
    "LivenessCheckOutcome",
    # Spatial Fusion
    "SpatialFusionEngine",
    "SpatialFusionResult",
    # Decision Engine
    "AttendanceDecisionEngine",
    "AttendanceDecision",
    "AttendanceGate",
    "GateResult",
    # Session Management
    "SessionNonceManager",
    "AttendanceSession",
    "SessionNonce",
]
