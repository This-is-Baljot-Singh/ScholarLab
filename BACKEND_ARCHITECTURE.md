# ScholarLab Backend Architecture - Hardened Foundation

**Date**: May 2026  
**Status**: Foundation Layer Established  
**Stack**: FastAPI + MongoDB + Celery

---

## Overview

This document describes the hardened backend architecture for ScholarLab, organized into **6 bounded contexts** with strict separation of concerns, zero-trust validation, and audit-ready infrastructure.

### Key Principles

1. **Zero-Trust Architecture**: Multi-modal validation (Device + Biometric + Spatial) for all attendance decisions
2. **Privacy-Preserving Inference**: All audio/LLM processing runs locally (Ollama/LangChain, NOT cloud APIs)
3. **Data Integrity**: Real-world test data only; immutable event-sourced logs
4. **Explainability**: ML predictions paired with SHAP attribution scores
5. **Audit-Ready**: Immutable, tamper-evident, Merkle-chained audit logs

---

## Directory Structure

```
backend/
├── app/
│   ├── config/
│   │   ├── environment.py       # 6 profiles: dev, staging, pilot, production
│   │   └── __init__.py
│   │
│   ├── contexts/                # 6 Bounded Contexts
│   │   ├── schemas.py           # Domain models (immutable events + mutable state)
│   │   ├── api_contracts.py     # Strict Pydantic request/response validation
│   │   ├── auth/                # Identity & Access Management
│   │   ├── attendance/          # Zero-trust attendance verification
│   │   ├── curriculum/          # Curriculum mapping & learning outcomes
│   │   ├── analytics/           # Risk scoring & SHAP explainability
│   │   ├── events/              # WebSocket & real-time events
│   │   └── audit/               # Audit trail & compliance
│   │
│   ├── logging/
│   │   ├── audit.py             # Immutable, tamper-evident audit logger
│   │   └── __init__.py
│   │
│   ├── jobs/
│   │   ├── celery_app.py        # Background job queue (Celery)
│   │   └── __init__.py
│   │       Tasks: audio transcription, SHAP inference, batch risk computation
│   │
│   └── main.py                  # FastAPI entry point (refactored)
│
├── migrations/
│   ├── runner.py                # MongoDB schema migrations & indexing
│   └── __init__.py
│
├── requirements.txt             # Updated with Celery, motor, etc.
└── .env.example                 # Environment variables template

```

---

## 1. Configuration Management (`app/config/environment.py`)

### Environment Profiles

Each environment has distinct settings:

| Profile | Database | Strictness | Audit | Use Case |
|---------|----------|-----------|-------|----------|
| **dev** | localhost | Relaxed | Minimal | Local development |
| **staging** | staging server | Moderate | Moderate | Testing |
| **pilot** | pilot-prod | Strict | Strict | Pilot institution |
| **production** | prod | Maximum | Maximum | Live deployment |

### Usage

```bash
# Run with environment
export SCHOLARLAB_ENV=production
python -m app.main

# Or via command line
SCHOLARLAB_ENV=staging celery worker

# Load settings in code
from app.config.environment import settings
print(settings.attendance.biometric_confidence_threshold)  # 0.98 in prod, 0.85 in dev
```

---

## 2. Bounded Contexts

### 2.1 Auth Context

**Responsibility**: Identity, authentication, session management

**Collections**:
- `users` (mutable) - Profile & auth credentials
- `devices` (mutable) - Device trust registry
- `sessions` (mutable) - Active WebSocket/HTTP sessions

**Key Models**:
- `UserInDB` - Identity + WebAuthn credentials
- `DeviceRegistration` - Device certificate chain
- `SessionState` - Multi-modal validation history

**API Contracts** (strict validation):
- `LoginRequest` - Email + complex password
- `UserCreateRequest` - Email + role + password validation
- `WebAuthnOptionsRequest/Response` - Biometric challenge

---

### 2.2 Attendance Context

**Responsibility**: Zero-trust attendance verification

**Collections**:
- `attendance_events` (IMMUTABLE, append-only) - Attendance log
- `geofences` (mutable) - Venue boundaries (2dsphere indexed)

**Zero-Trust Validation**:
```
All THREE signals required:
1. Device: registered device + certificate + session token
2. Biometric: face/fingerprint/WebAuthn (confidence > 0.95)
3. Spatial: geofence + beacon + network environment

If ANY signal fails → require faculty override (audit trail)
```

**Key Models**:
- `AttendanceEvent` - Immutable event with multi-modal signals
- `AttendanceEventSignals` - Device, biometric, spatial validation
- `GeofenceDefinition` - Venue boundary + network environment

**API Contracts**:
- `AttendanceVerifyRequest` - Strict validation of location precision, credentials
- `AttendanceVerifyResponse` - Response with signals validated + risk score

---

### 2.3 Curriculum Context

**Responsibility**: Learning outcomes, curriculum mapping, concept extraction

**Collections**:
- `courses` (mutable) - Course metadata
- `curriculum_nodes` (mutable) - DAG of topics/modules
- `curriculum_events` (IMMUTABLE, append-only) - Audio transcript concept extraction

**Privacy**: Audio transcription via local Ollama/Whisper ONLY (never cloud APIs)

**Key Models**:
- `CourseDefinition` - Course + enrollment
- `CurriculumNode` - DAG node with learning outcomes
- `CurriculumEvent` - Extracted concepts + inference lineage

**API Contracts**:
- `CurriculumNodeCreateRequest` - Strict: max 20 learning outcomes, validate URIs

---

### 2.4 Analytics Context

**Responsibility**: Risk scoring, SHAP explainability, student insights

**Collections**:
- `risk_events` (IMMUTABLE, append-only) - Risk scores + SHAP values
- (Reads from `attendance_events`, `curriculum_events`)

**Key Models**:
- `RiskEvent` - Risk score + SHAP explanation
- `RiskEventData` - Contributing factors

**Example Risk Calculation**:
```python
risk_score = (
    0.4 * recent_absence_rate +
    0.3 * engagement_score +
    0.2 * biometric_anomaly +
    0.1 * curriculum_mismatch
)
# SHAP values explain which factors contributed most
```

**API Contracts**:
- `RiskScoreRequest` - User + course + lookback window (7-365 days)
- `RiskScoreResponse` - Risk score + SHAP values + contributing factors

---

### 2.5 Events/WebSocket Context

**Responsibility**: Real-time faculty alerts, student notifications

**Collections**:
- (Reads/writes to event collections above)

**WebSocket Message Types**:
- `attendance_check_in` - Student arrival notification
- `curriculum_update` - Concept extraction complete
- `risk_alert` - High-risk student flagged
- `override_request` - Faculty override approval

**API Contracts**:
- `WebSocketMessageRequest` - Type-specific validated payload

---

### 2.6 Audit Context

**Responsibility**: Immutable compliance trail, tamper-evidence

**Collections**:
- `audit_logs` (IMMUTABLE, Merkle-chained, signed)
- `override_events` (IMMUTABLE)

**Tamper-Evidence**:
- Every entry includes `previous_log_hash` (Merkle chain)
- Hash is SHA256(entry_dict sorted JSON)
- Optional RSA signature for production
- Write-once MongoDB collection

**Key Models**:
- `AuditLogEntry` - Immutable log with Merkle chain
- `OverrideEvent` - Faculty override audit trail

**API Contracts**:
- `AuditLogQueryRequest` - Strict date range (7-365 days lookback)
- `AuditLogQueryResponse` - Tamper-evidence verification included

---

## 3. Schemas & Data Models

### Immutable Event Collections (Append-Only)

These collections NEVER UPDATE; new events are INSERTED only:

1. **attendance_events** - Student attendance verification
2. **curriculum_events** - Concept extraction from audio/syllabus
3. **risk_events** - Risk score computation + SHAP explanation
4. **override_events** - Faculty overrides (with audit trail)
5. **audit_logs** - All system actions (tamper-evident)

### Mutable State Collections

These collections support UPDATE for profile/configuration changes:

1. **users** - User profile
2. **devices** - Device registry
3. **sessions** - Active sessions (TTL-indexed)
4. **geofences** - Venue boundaries
5. **courses** - Course definitions
6. **curriculum_nodes** - Curriculum DAG

---

## 4. API Validation

All requests are **strictly validated** with Pydantic:

```python
# Example: AttendanceVerifyRequest
class AttendanceVerifyRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)  # Range validation
    longitude: float = Field(ge=-180, le=180)
    device_certificate_fingerprint: str = Field(regex="^[a-f0-9]{64}$")  # Regex
    password: str = Field(min_length=8, max_length=128)  # Length
    course_id: str = Field(min_length=1, max_length=64)
    
    @field_validator('latitude')
    def validate_location_precision(cls, v):
        # Custom: ≥4 decimal places = ~1 meter precision
```

**Output**: All responses wrapped in `APIResponse`:
```json
{
  "status": "success",
  "data": {...},
  "request_id": "uuid",
  "timestamp": "2026-05-04T14:30:00Z"
}
```

---

## 5. Audit Logging

### Immutable Audit Trail

Every request is logged immutably:

```python
await audit_logger.log(
    action=AuditAction.VERIFY,
    resource_type=AuditResourceType.ATTENDANCE,
    resource_id="attendance_event_123",
    actor="student_456",
    actor_role="student",
    old_value={"status": "pending"},
    new_value={"status": "marked"},
    success=True,
)
```

### Merkle Chain Verification

```python
# Verify no tampering between two logs
result = await audit_logger.verify_chain_integrity(
    start_log_id="log_001",
    end_log_id="log_050",
)
assert result["tampering_detected"] == False
```

---

## 6. MongoDB Migrations

### Setup Indexes & Schema

```bash
# Run migrations for dev
python -m migrations.runner dev

# Run for production
python -m migrations.runner production
```

### Migration Tracking

All migrations are tracked in `schema_migrations`:

```javascript
db.schema_migrations.find()
{
  "_id": ObjectId(),
  "version": "001_initial_schema",
  "description": "Create core collections",
  "applied_at": ISODate("2026-05-04"),
  "migration_type": "index_create"
}
```

### Key Indexes

| Collection | Index | Purpose |
|-----------|-------|---------|
| `attendance_events` | `user_id, timestamp` | Query by student |
| `attendance_events` | `session_id` (unique) | One event per session |
| `audit_logs` | `request_id` (unique) | Trace requests |
| `audit_logs` | `entry_hash` (unique) | Detect duplicates |
| `audit_logs` | `previous_log_hash` | Merkle chain |
| `geofences` | `boundary` (2dsphere) | Spatial queries |

---

## 7. Background Jobs (Celery)

### Heavy Tasks Offloaded to Workers

```bash
# Start worker
celery -A app.jobs.celery_app worker --loglevel=info

# Start scheduler (for periodic tasks)
celery -A app.jobs.celery_app beat --loglevel=info
```

### Available Tasks

1. **transcribe_audio** - Audio → text locally via Ollama
2. **compute_risk_with_shap** - Risk score + SHAP explanation
3. **batch_compute_risk** - Daily risk computation for all students
4. **archive_audit_logs** - Weekly archival of old audit logs

### Scheduled Tasks

```python
celery_app.conf.beat_schedule = {
    'batch-risk-computation': {
        'task': 'tasks.batch_compute_risk',
        'schedule': crontab(hour=2, minute=0),  # Daily 2 AM UTC
    },
    'archive-audit-logs': {
        'task': 'tasks.archive_audit_logs',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Weekly Sunday 3 AM
    },
}
```

### Example Task

```python
# Call async
task = transcribe_audio.apply_async(
    args=("session_123", "/path/to/audio.wav"),
    queue="default",
)

# Check status
status = get_task_status(task.id)
# {state: "PENDING", result: None}
# Later: {state: "SUCCESS", result: {"transcription": "..."}}
```

---

## 8. Environment Variable Configuration

Create `.env`:

```bash
# Core
SCHOLARLAB_ENV=production

# Database
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=scholarlab_prod

# Auth
SECRET_KEY=<rotate-quarterly>
WEBAUTHN_RP_ID=scholarlab.institution.edu
WEBAUTHN_ORIGIN=https://scholarlab.institution.edu

# Job Queue
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Ollama (local inference)
OLLAMA_BASE_URL=http://localhost:11434

# Compliance
AUDIT_LOG_SIGNING=true
AUDIT_LOG_ARCHIVE_S3_BUCKET=scholarlab-audit
```

---

## 9. Deployment Checklist

### Before Pilot

- [ ] Run migrations: `python -m migrations.runner pilot`
- [ ] Verify Merkle chain integrity of audit logs
- [ ] Configure Ollama for audio transcription
- [ ] Test SHAP inference pipeline
- [ ] Load realistic (real-world) seed data
- [ ] Verify all API contracts via integration tests
- [ ] Review security checklist (zero-trust, privacy, data integrity)

### Before Production

- [ ] All pilot checkpoints passed
- [ ] Audit log signing enabled (RSA keypair rotated)
- [ ] MongoDB backup/restore tested
- [ ] Celery worker redundancy configured
- [ ] Monitoring/alerting in place
- [ ] Compliance audit completed

---

## 10. Integration Points

### FastAPI Router Structure

Each bounded context has its router:

```python
# app/main.py
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(attendance_router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(curriculum_router, prefix="/api/curriculum", tags=["Curriculum"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(audit_router, prefix="/api/audit", tags=["Audit"])
```

### Middleware for Audit

```python
@app.middleware("http")
async def audit_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    set_request_id(request_id)
    
    # Extract actor from JWT
    actor = extract_actor_from_jwt(request)
    set_actor(actor)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

---

## 11. Testing Strategy

### Unit Tests

```bash
pytest tests/unit/ -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
# Spins up test MongoDB + Redis
```

### Zero-Trust Validation Tests

```bash
pytest tests/zero_trust/ -v
# Verify all 3 signals required
# Test rejection when any signal fails
```

---

## 12. Monitoring & Observability

### Metrics to Track

- Attendance verification latency (target: <500ms)
- Risk score computation time (target: <2s)
- Audit log write latency (target: <100ms)
- Celery task queue depth (alert if >1000)
- MongoDB index hit rate (target: >95%)

### Logging

All logs are JSON-formatted with correlation IDs:

```json
{
  "timestamp": "2026-05-04T14:30:00Z",
  "level": "INFO",
  "logger": "app.routers.attendance",
  "message": "Attendance verified",
  "context": {
    "request_id": "uuid",
    "actor": "student_123"
  },
  "extra": {
    "course_id": "MATH-101",
    "signals": {"device": true, "biometric": true, "spatial": true}
  }
}
```

---

## 13. Next Steps

1. **Implement routers** - Convert existing routers to use new schemas & audit logging
2. **Integrate Ollama** - Setup local audio transcription
3. **Load test data** - Use real institutional data (de-identified)
4. **Run migrations** - Initialize MongoDB schema
5. **Launch pilot** - Incremental rollout to test institution

---

## References

- [ScholarLab Production Rules](/memories/repo/scholarlab.md)
- [Domain-Driven Design](https://www.domainlanguage.com/ddd/)
- [Event Sourcing](https://www.eventstore.com/blog/event-sourcing-explained)
- [Zero Trust Architecture](https://www.nist.gov/publications/zero-trust-architecture)
