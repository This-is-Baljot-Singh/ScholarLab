"""
ZERO-TRUST ATTENDANCE VERIFICATION
Quick Integration & Testing Guide (May 2026)

Status: BACKEND COMPLETE ✓
All 5 core services + router + MongoDB collections ready.
Frontend integration begins next phase.
"""


# ============================================================================
# QUICK START: TESTING THE PIPELINE
# ============================================================================

MANUAL_TEST_FLOW = """
Prerequisites:
  - MongoDB running with tz_aware=True
  - FastAPI server running (uvicorn app.main:app --reload)
  - Redis running (for Celery, if using background jobs)

Step 1: Faculty Creates Attendance Session
────────────────────────────────────────────
curl -X POST http://localhost:8000/api/attendance/sessions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <FACULTY_TOKEN>" \\
  -d '{
    "course_id": "MATH-101",
    "geofence_id": "room-101",
    "lecture_title": "Calculus Lecture 5",
    "duration_minutes": 50,
    "expected_students": 30
  }'

Response:
{
  "session_id": "abc123xyz789...",
  "started_at": "2026-05-15T14:00:00Z",
  "expires_at": "2026-05-15T14:50:00Z",
  "expected_duration_minutes": 50
}

→ Save session_id for next steps


Step 2: Student Requests Nonce
───────────────────────────────
curl -X POST http://localhost:8000/api/attendance/sessions/abc123xyz789.../nonce \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <STUDENT_TOKEN>" \\
  -d '{
    "session_id": "abc123xyz789...",
    "device_id": "device-iphone-12pro-xxxxx"
  }'

Response:
{
  "nonce": "secure_random_token_here_xxxxx...",
  "expires_in_seconds": 300,
  "session_id": "abc123xyz789..."
}

→ Nonce is single-use, expires in 5 minutes
→ Bind to this exact device and session


Step 3: Student Verifies Attendance (Full Pipeline)
─────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/attendance/checkin \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <STUDENT_TOKEN>" \\
  -d '{
    "session_id": "abc123xyz789...",
    "course_id": "MATH-101",
    "geofence_id": "room-101",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "device_id": "device-iphone-12pro-xxxxx",
    "device_signature": {
      "signature": "base64_encoded_signature_here...",
      "timestamp": "2026-05-15T14:05:00Z"
    },
    "nonce": "secure_random_token_here_xxxxx...",
    "biometric_outcome": "pass",
    "biometric_confidence": 0.97,
    "liveness_score": 0.92,
    "observed_beacons": [
      {"uuid": "beacon-room-101-a", "rssi": -45},
      {"uuid": "beacon-room-101-b", "rssi": -48}
    ],
    "floor": 1,
    "magnetic_field": [20.5, 15.3, 48.2]
  }'

Response (if ALL 6 gates pass):
{
  "decision_id": "decision_xyz123...",
  "attendance_marked": true,
  "reasoning": "✓ ALL GATES PASSED: Attendance marked",
  "gates_passed": 6,
  "gates_failed": [],
  "timestamp": "2026-05-15T14:05:30Z"
}

Response (if ANY gate fails):
{
  "decision_id": "decision_xyz456...",
  "attendance_marked": false,
  "reasoning": "✗ REJECTED: Failed gates: nonce, biometric",
  "gates_passed": 4,
  "gates_failed": ["nonce", "biometric"],
  "timestamp": "2026-05-15T14:05:30Z"
}


Step 4: Faculty Reviews Session Statistics
─────────────────────────────────────────────
curl -X GET http://localhost:8000/api/attendance/sessions/abc123xyz789.../stats \\
  -H "Authorization: Bearer <FACULTY_TOKEN>"

Response:
{
  "session_id": "abc123xyz789...",
  "course_id": "MATH-101",
  "started_at": "2026-05-15T14:00:00Z",
  "expires_at": "2026-05-15T14:50:00Z",
  "is_active": true,
  "expected_students": 30,
  "checked_in": 28,
  "attendance_rate": 0.933,
  "nonce_attempts": 30,
  "nonce_failures": 2,
  "nonce_success_rate": 0.933
}
"""


# ============================================================================
# DATABASE SETUP: REQUIRED COLLECTIONS & INDEXES
# ============================================================================

MONGODB_SETUP = """
Collections to Create (Run at Startup):

1. attendance_sessions
   db.createCollection("attendance_sessions")
   db.attendance_sessions.createIndex({"session_id": 1}, {unique: true})
   db.attendance_sessions.createIndex({"course_id": 1})
   db.attendance_sessions.createIndex({"faculty_id": 1})
   db.attendance_sessions.createIndex({"expires_at": 1})
   db.attendance_sessions.createIndex({"started_at": 1}, {expireAfterSeconds: 604800})

2. session_nonces
   db.createCollection("session_nonces")
   db.session_nonces.createIndex({"nonce": 1}, {unique: true, sparse: true})
   db.session_nonces.createIndex({"session_id": 1})
   db.session_nonces.createIndex({"user_id": 1})
   db.session_nonces.createIndex({"device_id": 1})
   db.session_nonces.createIndex({"expires_at": 1}, {expireAfterSeconds: 0})

3. nonce_audit_logs
   db.createCollection("nonce_audit_logs")
   db.nonce_audit_logs.createIndex({"nonce_hash": 1})
   db.nonce_audit_logs.createIndex({"session_id": 1})
   db.nonce_audit_logs.createIndex({"timestamp": 1})
   db.nonce_audit_logs.createIndex({"timestamp": 1}, {expireAfterSeconds: 7776000})

4. device_bindings
   db.createCollection("device_bindings")
   db.device_bindings.createIndex({"device_id": 1}, {unique: true})
   db.device_bindings.createIndex({"user_id": 1})
   db.device_bindings.createIndex({"device_certificate_fingerprint": 1}, {unique: true})
   db.device_bindings.createIndex({"public_key_hash": 1})
   db.device_bindings.createIndex({"certificate_expiry": 1})

5. biometric_verifications
   db.createCollection("biometric_verifications")
   db.biometric_verifications.createIndex({"session_id": 1}, {unique: true})
   db.biometric_verifications.createIndex({"nonce": 1}, {unique: true})
   db.biometric_verifications.createIndex({"timestamp": 1}, {expireAfterSeconds: 7776000})

6. spatial_fusion_results
   db.createCollection("spatial_fusion_results")
   db.spatial_fusion_results.createIndex({"session_id": 1}, {unique: true})
   db.spatial_fusion_results.createIndex({"timestamp": 1})

7. location_history
   db.createCollection("location_history")
   db.location_history.createIndex({"user_id": 1})
   db.location_history.createIndex({\"timestamp\": -1})
   db.location_history.createIndex({"timestamp": 1}, {expireAfterSeconds: 7776000})

8. gate_audit_logs
   db.createCollection("gate_audit_logs")
   db.gate_audit_logs.createIndex({"decision_id": 1})
   db.gate_audit_logs.createIndex({"timestamp": 1})

9. attendance_decisions
   db.createCollection("attendance_decisions")
   db.attendance_decisions.createIndex({"decision_id": 1}, {unique: true})
   db.attendance_decisions.createIndex({"session_id": 1}, {unique: true})
   db.attendance_decisions.createIndex({"user_id": 1})
   db.attendance_decisions.createIndex({"course_id": 1})

10. beacon_config
    db.createCollection("beacon_config")
    db.beacon_config.createIndex({"geofence_id": 1}, {unique: true})

Python: Call at Startup
─────────────────────

from app.contexts.attendance import (
    SessionNonceManager,
    DeviceRegistrationService,
    BiometricLivenessService,
    SpatialFusionEngine,
    AttendanceDecisionEngine,
)

@app.on_event("startup")
async def initialize_attendance_services():
    session_mgr = SessionNonceManager(db)
    await session_mgr.initialize()
    
    device_svc = DeviceRegistrationService(db)
    await device_svc.initialize()
    
    biometric_svc = BiometricLivenessService(db)
    await biometric_svc.initialize()
    
    spatial_engine = SpatialFusionEngine(db)
    await spatial_engine.initialize()
    
    decision_engine = AttendanceDecisionEngine(db)
    await decision_engine.initialize()
    
    logger.info("Attendance services initialized ✓")
"""


# ============================================================================
# GATE-BY-GATE TESTING
# ============================================================================

GATE_TESTING = """
Test Each Gate Independently (for debugging):

Gate 1: Device Verification (D_t)
─────────────────────────────────
Device must be registered and trusted.

Setup:
  1. Register device with DeviceRegistrationService.register_device()
  2. Admin approves with .approve_device()
  3. Get WebAuthn public key

Test:
  from app.contexts.attendance import DeviceRegistrationService
  svc = DeviceRegistrationService(db)
  result = await svc.verify_device_signature("device-123", signature_data)
  assert result == True  # Device gate passes ✓

Expected Failures:
  - Device not registered → False
  - Device not approved (is_trusted=False) → False
  - Certificate expired → False
  - Failed verification count > 10 → False


Gate 2: Cryptographic Signature (K_t)
──────────────────────────────────────
Request must be signed with device's private key.

Test:
  # Frontend signs request
  const signature = await device.sign(requestData);
  
  # Backend verifies
  from webauthn import verify_authentication_response
  verified = verify_authentication_response(
    credential=device.credential,
    credential_assertion_response=signature,
  )
  assert verified == True  # Crypto gate passes ✓

Expected Failures:
  - Invalid signature → False
  - Signature doesn't match request → False
  - Device revoked → False


Gate 3: Nonce Validation (N_t)
───────────────────────────────
Nonce must be fresh, unused, correctly bound.

Test:
  from app.contexts.attendance import SessionNonceManager
  mgr = SessionNonceManager(db)
  
  # Request nonce
  nonce_record = await mgr.create_nonce(
    "session-123", "user-456", "device-789"
  )
  
  # Validate nonce
  await mgr.validate_nonce(
    nonce_record.nonce,
    "session-123", "user-456", "device-789"
  )  # Passes ✓
  
  # Try again (should fail, nonce deleted)
  await mgr.validate_nonce(...)  # Raises ValueError ✓

Expected Failures:
  - Nonce not found (already used) → ValueError
  - Nonce expired (>5 min) → ValueError
  - session_id mismatch → ValueError (session fixation)
  - user_id mismatch → ValueError (identity spoofing)
  - device_id mismatch → ValueError (device spoofing)


Gate 4: Biometric Liveness (B_t)
─────────────────────────────────
Biometric must pass liveness, confidence, and anti-spoofing.

Test:
  from app.contexts.attendance import BiometricLivenessService
  svc = BiometricLivenessService(db)
  
  # Record verification
  await svc.record_verification(
    user_id="user-456",
    device_id="device-789",
    session_id="session-123",
    nonce=nonce_record.nonce,
    modality="face",
    outcome="pass",
    confidence=0.97,
    liveness_score=0.92,
    anti_spoofing_passed=True,
  )
  
  # Check verification
  valid = await svc.is_verification_valid("session-123", "face")
  assert valid == True  # Biometric gate passes ✓

Expected Failures:
  - outcome != "pass" → False
  - confidence < 0.95 → False
  - liveness_score < 0.80 → False
  - anti_spoofing_passed=False → False
  - verification expired (>1 hour) → False


Gate 5: Multi-Modal Validation (M_t)
──────────────────────────────────────
Device, Biometric, and Spatial all verified.

Test:
  device_ok = True  # Gate 1 passed
  biometric_ok = True  # Gate 4 passed
  spatial_ok = True  # Gate 6 passed
  
  from app.contexts.attendance.decision_engine import AttendanceDecisionEngine
  engine = AttendanceDecisionEngine(db)
  result = await engine.check_multimodal_gate(device_ok, biometric_ok, spatial_ok)
  assert result.passed == True  # Multi-modal gate passes ✓

Expected Failures:
  - Any single modality False → False


Gate 6: Geofence + Spatial Fusion (G_t)
───────────────────────────────────────
6-signal composite confidence C_t >= 0.70

Test:
  from app.contexts.attendance import SpatialFusionEngine
  engine = SpatialFusionEngine(db)
  
  result = await engine.compute_composite_confidence(
    session_id="session-123",
    user_id="user-456",
    geofence_id="room-101",
    latitude=40.7128,
    longitude=-74.0060,
    observed_beacons=[...],
    floor=1,
    magnetic_field_vector=(20.5, 15.3, 48.2),
  )
  
  assert result.composite_confidence >= 0.70  # Spatial gate passes ✓
  assert result.confidence_level in ["high", "medium"]

Signal Breakdown:
  - g_t (geofence): Haversine distance from room center
  - r_t (beacon): BLE proximity score
  - u_t (velocity): Kinematic feasibility
  - b_t (building): Floor match
  - m_t (magnetic): Field signature
  - l_t (history): Trajectory plausibility
"""


# ============================================================================
# ENVIRONMENT SETUP: Configuration
# ============================================================================

ENV_SETUP = """
Environment Configuration:

.env.development
─────────────────
MONGODB_URI=mongodb://localhost:27017/scholarlab-dev
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
ATTENDANCE_BIOMETRIC_THRESHOLD=0.85
ATTENDANCE_SPATIAL_THRESHOLD=0.70
NONCE_VALIDITY_SECONDS=300
SESSION_DURATION_MINUTES=50

.env.production
────────────────
MONGODB_URI=mongodb+srv://prod_user:pass@scholarlab-prod.mongodb.net/scholarlab-prod
ENVIRONMENT=production
LOG_LEVEL=INFO
ATTENDANCE_BIOMETRIC_THRESHOLD=0.98  # Stricter
ATTENDANCE_SPATIAL_THRESHOLD=0.75
NONCE_VALIDITY_SECONDS=300
SESSION_DURATION_MINUTES=50
# Enable RSA signing:
ENABLE_RSA_AUDIT_SIGNING=true
RSA_PRIVATE_KEY_PATH=/etc/scholarlab/audit_private.key
RSA_PUBLIC_KEY_PATH=/etc/scholarlab/audit_public.key
"""


# ============================================================================
# MONITORING & OBSERVABILITY
# ============================================================================

MONITORING = """
Key Metrics to Track:

Per Endpoint:
  ├─ POST /attendance/sessions
  │  └─ Latency, errors, session creation rate
  │
  ├─ POST /attendance/sessions/{id}/nonce
  │  └─ Nonce generation latency, rate limit hits
  │
  ├─ POST /attendance/checkin
  │  └─ Full pipeline latency, gate pass rates, decision distribution
  │
  └─ GET /attendance/sessions/{id}/stats
     └─ Query latency

Per Gate (in checkin endpoint):
  ├─ Device gate: pass rate, cert expiry alerts
  ├─ Crypto gate: signature verification errors
  ├─ Nonce gate: expiry events, rate limit hits, replay attempts
  ├─ Biometric gate: liveness failures, spoofing detections
  ├─ Multi-modal: incomplete signal counts
  └─ Spatial gate: anomaly frequency (wrong floor, beacon mismatch, velocity)

Alerts:
  ├─ Attendance decision rejection rate > 10% (possible fraud)
  ├─ Device certificate expiry < 7 days
  ├─ Nonce rate limit hits (brute force?)
  ├─ Replay attack detection (nonce reuse attempts)
  ├─ Magnetic anomalies > 20% (spoofing?)
  └─ Session creation failures

Logging:
  ├─ All decisions logged (decision_id, user_id, gates_passed, timestamp)
  ├─ All gate failures logged with reason
  ├─ All nonce events logged (created, used, expired, failed)
  ├─ All device registrations & approvals logged
  └─ Audit trail immutable (for forensics)

Query Examples:
  # Count decisions by outcome
  db.attendance_decisions.aggregate([
    {$group: {_id: "$attendance_marked", count: {$sum: 1}}}
  ])
  
  # Gate pass rates
  db.gate_audit_logs.aggregate([
    {$group: {_id: "$gate", passed_count: {$sum: {$cond: ["$passed", 1, 0]}}, total: {$sum: 1}}},
    {$project: {pass_rate: {$divide: ["$passed_count", "$total"]}}}
  ])
  
  # Nonce replay attempt rate
  db.nonce_audit_logs.aggregate([
    {$match: {event: {$in: ["failed", "expired"]}}},
    {$group: {_id: null, failure_count: {$sum: 1}}},
    {$lookup: {from: "nonce_audit_logs", pipeline: [{$match: {event: "created"}}], as: "total"}},
  ])
"""


# ============================================================================
# ERROR HANDLING & COMMON ISSUES
# ============================================================================

TROUBLESHOOTING = """
Common Issues & Solutions:

Issue 1: "Session not active"
────────────────────────────
Cause: Session expired or closed
Fix:   Check session.expires_at > now, or faculty closed session too early
Test:  GET /attendance/sessions/{session_id}/stats → check is_active=true

Issue 2: "Nonce not found" or "already used"
──────────────────────────────────────────────
Cause: Nonce already consumed in previous check-in attempt
Fix:   Request new nonce
Test:  POST /attendance/sessions/{session_id}/nonce (fresh)

Issue 3: "Nonce session_id mismatch"
──────────────────────────────────────
Cause: Using nonce from different session
Fix:   Request nonce for current session, check bindings
Test:  Ensure nonce.session_id == request.session_id

Issue 4: "Device certificate expired"
──────────────────────────────────────
Cause: Device cert validity_period passed
Fix:   Device must re-register with new cert
Test:  Device re-registration flow

Issue 5: "Biometric confidence < 0.95"
───────────────────────────────────────
Cause: Poor biometric quality or spoofing attempt
Fix:   Request biometric verification again
Test:  Frontend retries with better image/fingerprint

Issue 6: "Composite confidence < 0.70"
──────────────────────────────────────
Cause: One or more spatial signals weak
Fix:   Check location accuracy, beacon coverage, magnetic calibration
Test:  POST /attendance/checkin with debug output (see risk_factors)

Issue 7: "Attendance decision error: internal server error"
────────────────────────────────────────────────────────────
Cause: Database error or service not initialized
Fix:   Check MongoDB connectivity, call .initialize() on services
Test:  Check server logs, restart services

Issue 8: "Rate limit exceeded"
──────────────────────────────
Cause: Too many nonce requests (>20/hour)
Fix:   Student waited, retry after cooldown
Test:  Clear nonce_audit_logs and retry
"""


# ============================================================================
# NEXT PHASE: FRONTEND INTEGRATION
# ============================================================================

FRONTEND_NEXT_STEPS = """
Frontend Development (React + TypeScript):

Implement useZeroTrustAttendance Hook
────────────────────────────────────
File: frontend/src/hooks/useZeroTrustAttendance.ts

Exports:
  const {
    requestNonce,
    verifyAttendance,
    loading,
    error,
    decision,
  } = useZeroTrustAttendance(courseId);

Sub-Hooks to Implement:
  1. useWebAuthn() - Device credential challenge/response
  2. useGeolocation() - Location with ≥4 decimal precision (~1m)
  3. useBiometric() - Biometric scan (face/fingerprint)
  4. useBeaconScanning() - BLE beacon discovery
  5. useMagnetometer() - Magnetometer readings (x, y, z)
  6. useCompositeVerification() - Orchestrate all signals

Usage Pattern:
  const handleCheckIn = async () => {
    const {nonce} = await requestNonce();
    const signals = {
      latitude, longitude,
      biometric: {outcome, confidence, liveness},
      beacons,
      magnetic: [x, y, z],
    };
    const decision = await verifyAttendance({nonce, signals});
    if (decision.attendance_marked) showSuccess();
    else showError(decision.reasoning);
  };

Components to Create:
  ├─ AttendanceCheckInFlow.tsx
  │  ├─ Displays session info
  │  ├─ Collects device signals
  │  ├─ Shows gate progress/results
  │  └─ Displays final decision
  │
  ├─ SessionCreationModal.tsx (Faculty)
  │  ├─ Create new session
  │  ├─ Set duration, expected students
  │  └─ Display session_id for sharing
  │
  └─ SessionStatisticsPanel.tsx (Faculty)
     ├─ Real-time check-in count
     ├─ Gate pass rates
     └─ Export attendance CSV

API Integration:
  POST /api/attendance/sessions
  POST /api/attendance/sessions/{id}/nonce
  POST /api/attendance/checkin
  GET /api/attendance/sessions/{id}/stats

Tests to Add:
  ├─ Unit: Each hook independently
  ├─ Integration: Full check-in flow
  ├─ Negative: Expired nonce, wrong device, etc.
  └─ Performance: Latency per gate
"""


print(__doc__)
