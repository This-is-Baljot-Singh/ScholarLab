# ScholarLab: Complete System Architecture & Integration

## Overview: 3 Phases

ScholarLab is a **zero-trust, privacy-preserving education verification platform** built in 3 phases:

| Phase | Focus | Key Technologies | Status |
|-------|-------|-----------------|--------|
| **Phase 1** | Production Foundation | Environment profiles, audit logging, Celery, MongoDB migrations | ✅ Complete |
| **Phase 2** | Zero-Trust Attendance Verification | WebAuthn, biometric liveness, spatial fusion, 6-gate decision | ✅ Complete |
| **Phase 3** | Privacy-Preserving Curriculum Pipeline | Local Whisper, embeddings, cosine similarity, faculty verification | ✅ Complete |

---

## Phase 1: Production Foundation (Completed)

### Purpose
Establish hardened backend infrastructure with zero-trust principles, immutable audit logging, and environment-aware configuration.

### Key Files
- `backend/app/config/environment.py` (300+ lines) - 6 environment profiles with progressive strictness
- `backend/app/logging/audit.py` (300+ lines) - Merkle-chain audit logging
- `backend/migrations/runner.py` - Idempotent MongoDB schema migrations
- `backend/app/jobs/celery_app.py` - Background job queue

### Collections Created (11)
**Mutable (state):**
- users, devices, sessions, geofences, courses

**Immutable (events):**
- attendance_events, curriculum_events, risk_events, override_events

**Audit:**
- audit_logs (Merkle-chained, tamper-evident)

### Guardrails
```
🔒 Zero-Trust Validation: All inputs validated (Pydantic strict mode)
🔒 Data Integrity: Merkle chains link audit entries
🔒 Environment-Aware: 6 profiles (dev→production) with strictness ramp
🔒 Immutability: Event collections append-only (no updates)
🔒 Explainability: Formula versioning for all ML/decision outputs
```

---

## Phase 2: Zero-Trust Attendance Verification (Completed)

### Architecture: 6-Gate Hard AND Decision

$$A_t = D_t \land K_t \land M_t \land N_t \land B_t \land G_t$$

All 6 gates must pass. **No bypass. No override.**

### Gate Definitions

| Gate | Component | Check | Pass Criteria |
|------|-----------|-------|---------------|
| **D_t** | Device | Registered + trusted? | ✓ device_id known, cert valid, not cloned |
| **K_t** | Crypto | Signature valid? | ✓ WebAuthn signature verified, device approved |
| **M_t** | Multi-Modal | All 3 modes present? | ✓ device + biometric + spatial all verified |
| **N_t** | Nonce | Fresh & bound? | ✓ nonce exists, not expired, not replayed, triplet valid |
| **B_t** | Biometric | Liveness pass? | ✓ outcome=pass, confidence≥0.95, liveness≥0.80 |
| **G_t** | Geofence | Spatial confidence high? | ✓ composite_confidence≥0.70, no anomalies |

### 5 Core Services

1. **DeviceRegistrationService** (400 lines)
   - Cryptographic device binding via WebAuthn
   - Clone detection (counter verification)
   - Deterministic device_id (SHA256 hash)

2. **BiometricLivenessService** (450 lines)
   - Privacy-preserving (outcome-only storage)
   - Rate limiting (10/hour per device)
   - Single-use nonce binding

3. **SpatialFusionEngine** (650 lines)
   - 6-signal composite formula: $C_t = 0.25g_t + 0.20r_t + 0.15u_t + 0.15b_t + 0.15m_t + 0.10l_t$
   - Independent signal computation
   - Anomaly detection (flags outside_geofence, impossible_velocity, etc.)

4. **DecisionEngine** (500 lines)
   - Hard-gate conjunction (all 6 must pass)
   - Immutable decision storage
   - No modification post-decision

5. **SessionManager** (550 lines)
   - Session lifecycle management
   - Single-use nonce validation
   - Rate limiting (20/hour per device)

### API: Attendance Verification Router

```
POST /attendance/sessions                    → Faculty creates session
POST /attendance/sessions/{id}/nonce          → Student requests nonce
POST /attendance/checkin                      → Student submits verification
GET  /attendance/sessions/{id}/stats          → Faculty views statistics
```

### Response Example

```json
{
  "attendance_marked": true,
  "decision_id": "decision_999",
  "gates_passed": 6,
  "gates_failed": 0,
  "gates_breakdown": {
    "device_verification": true,
    "crypto_verification": true,
    "multi_modal_verification": true,
    "nonce_verification": true,
    "biometric_verification": true,
    "geofence_verification": true
  },
  "composite_spatial_confidence": 0.82,
  "generated_at": "2025-05-21T10:42:00Z"
}
```

### Privacy Guarantees

✅ **Biometric Privacy:** No raw biometric data stored (outcome + confidence only)
✅ **Location Privacy:** Only spatial signals stored (not raw coordinates)
✅ **Device Privacy:** Only public keys + hashes (no hardware IDs)
✅ **Session Privacy:** Short-lived nonces (5 min), single-use

---

## Phase 3: Privacy-Preserving Curriculum Pipeline (Completed)

### Architecture: 5-Service Audio→Topics→Mapping→Verification→Unlock

```
Audio File (MP3/M4A/OGG)
    ↓
[1. LocalWhisperService]     ← Ollama (local, no cloud)
    ↓ Transcript
Topic Extraction
    ↓
[2. TopicExtractionService]  ← TF-IDF + n-grams + clustering
    ↓ CandidateTopic[]
Embeddings + Cosine Similarity
    ↓
[3. SyllabusMatchingAgent]   ← sentence-transformers (local)
    ↓ TopicMappingResult (s_j scores)
Below-Threshold Filtering
    ↓
[4. VerificationAgent]       ← Faculty manual review
    ↓ VerificationTask[]
Attendance-Gated Unlock
    ↓
[5. ResourceUnlockService]   ← Only if A_t = True
    ↓
Student resources unlocked
```

### 4 ML Services (All Local, NO Cloud APIs)

#### 1. LocalWhisperService

```python
# Speech-to-text via Ollama (local inference)
transcript_result = await whisper_svc.transcribe_audio(
    audio_file_path="/tmp/lecture.mp3",
    session_id="sess_12345",
    language="en",
)
# Returns: transcript, segments, language, duration, inference_time
```

**Requirements:**
- Ollama running: `ollama serve`
- Model: `ollama pull whisper`
- ffmpeg for format conversion (16kHz WAV)

#### 2. TopicExtractionService

```python
# Extract candidate topics from transcript
extraction_result = topic_svc.extract_topics(
    transcript=transcript_text,
    session_id="sess_12345",
    top_k=15,
)
# Returns: CandidateTopic[] {topic, frequency, confidence, source}
```

**Algorithm:**
- TF-based keyword extraction + 108 stopword filtering
- Bigram/trigram phrase extraction
- Clustering via substring deduplication
- Confidence: min(1.0, frequency / 10)

#### 3. SyllabusMatchingAgent (Core ML)

```python
# Match topics to curriculum nodes via cosine similarity
mapping_result = await matcher.match_topics_to_nodes(
    session_id="sess_12345",
    course_id="CS101",
    topics=extraction_result.candidates,
    top_k_matches=3,
)
# Returns: TopicMappingResult with all s_j scores
```

**Formula (Cosine Similarity):**
$$s_j = \cos(E(T_t), e_j) = \frac{E(T_t) \cdot e_j}{||E(T_t)|| \cdot ||e_j||}$$

**Model:** all-MiniLM-L6-v2 (sentence-transformers)
- 384-dimensional vectors
- ~22 MB (downloaded once, cached locally)
- ~50 ms per embedding

**Caching:**
- Embeddings cached in MongoDB: `curriculum_node_embeddings_cache`
- Indexed by node_id (unique)
- Avoids re-computation for repeated queries

**Threshold Filtering:**
- Default δ = 0.6
- Above δ → approved mappings
- Below δ → flagged for verification

#### 4. VerificationAgent (Faculty Review)

```python
# Create verification tasks for below-threshold mappings
verif_tasks = await verif_agent.create_verification_tasks(
    session_id="sess_12345",
    course_id="CS101",
    below_threshold_matches=below_threshold,
)
# Returns: VerificationTask[] (status=pending)
```

**Faculty Actions:**
- **Approve:** Confirms suggested mapping (s_j becomes 1.0)
- **Reject:** Rejects incorrect mapping
- **Correct:** Provides correct curriculum node

**Workflow:**
```
pending → approved         (faculty confirmed)
       → rejected         (faculty rejected)
       → corrected        (faculty provided correction)
```

#### 5. ResourceUnlockService (Attendance-Gated)

```python
# Progressively unlock resources only if A_t = True
unlock_result = await unlock_svc.unlock_resources_for_student(
    user_id="student_42",
    session_id="sess_12345",
    course_id="CS101",
    attendance_verified=True,    # A_t = True (hard gate)
    attendance_decision_id="decision_999",
    curriculum_node_ids=verified_node_ids,
)
# Returns: ProgressiveUnlock with unlocked resource IDs
```

**Resource Types:**
- LECTURE_NOTES, SLIDES, RECORDINGS, SUPPLEMENTARY, ASSIGNMENTS, SOLUTIONS

**Gate Equation:**
$$\text{Resource Unlock} = A_t$$

If A_t = True → resources unlocked
If A_t = False → resources remain locked (no bypass)

### Celery Tasks (Orchestration)

#### Task 1: `curriculum_pipeline`

Chains all 5 services end-to-end:

```python
# Faculty uploads audio → task queued
curriculum_pipeline.delay(
    session_id="sess_12345",
    course_id="CS101",
    audio_file_path="/tmp/curriculum_audio/sess_12345.mp3",
)

# Result (T≈51s):
{
    "session_id": "sess_12345",
    "stage": "verification_needed",  # If below-threshold tasks exist
    "topics_extracted": 15,
    "mapped_topics": 15,
    "total_matches": 45,
    "below_threshold": 12,
    "verification_tasks_created": 12,
}
```

**Timeline:**
- T=0s: Start transcription
- T=30s: Transcript ready
- T=35s: Topics extracted
- T=50s: Mappings complete
- T=51s: Verification tasks queued

#### Task 2: `unlock_resources_for_session`

Called after attendance verification completes:

```python
# After all students check in with A_t = True
unlock_resources_for_session.delay(
    session_id="sess_12345",
    course_id="CS101",
    verified_curriculum_node_ids=["node_001", "node_002", ...],
)

# Result:
{
    "students_with_attendance": 42,
    "resources_unlocked": 126,
    "total_unlock_events": 42,
}
```

### 7 New MongoDB Collections

| Collection | Purpose | Size |
|-----------|---------|------|
| curriculum_topic_mappings | Topic extraction results | Per session |
| curriculum_node_embeddings_cache | Precomputed 384-D vectors | Per course (~22MB) |
| curriculum_verification_tasks | Faculty review queue | Per below-threshold match |
| curriculum_verified_mappings | Faculty decisions | Per verified mapping |
| curriculum_resources | Lecture materials | Per node |
| curriculum_resource_accesses | Audit trail (TTL 90d) | Per access |
| curriculum_progressive_unlocks | Unlock events | Per student per session |

### Privacy Guarantees

✅ **ZERO Cloud APIs:** All processing local
- Ollama (local Whisper, not cloud transcription)
- sentence-transformers (local embeddings, not HuggingFace API)
- FFmpeg (local audio conversion)

✅ **Outcome-Only Storage:**
- Audio: transcribed → deleted
- Embeddings: cached as vectors (no source recovery)

✅ **Attendance-Gated:** Resources unlock only if A_t = True

✅ **Audit Trail:**
- Every resource access logged
- Faculty decisions immutable
- 90-day TTL for access logs

---

## System-Wide Integration

### Complete Data Flow: Student Attends Class

```
Timeline:

1. SETUP (Faculty)
   ├─ Create course (CS101)
   ├─ Create curriculum nodes (Module 1, Module 2, ...)
   ├─ Register resources (slides, notes, recordings)
   └─ Upload lecture recording (MP3)

2. CURRICULUM PIPELINE (Automated)
   ├─ [Celery] curriculum_pipeline starts
   ├─ Transcribe audio (Ollama Whisper) → "machine learning is..."
   ├─ Extract topics (TF-IDF) → ["machine learning", "neural networks", ...]
   ├─ Match to syllabus (cosine s_j) → 45 mappings found
   ├─ Filter by δ=0.6 → 12 below threshold
   └─ Create verification tasks → VerificationAgent

3. FACULTY VERIFICATION (Manual)
   ├─ Faculty reviews pending tasks
   ├─ Approves/rejects/corrects mappings
   └─ Verified mappings stored → curriculum_verified_mappings

4. ATTENDANCE SESSION (Zero-Trust)
   ├─ Faculty creates session → AttendanceSession
   ├─ Faculty shares session ID with class
   └─ (Session expires in 50-120 minutes)

5. STUDENT CHECK-IN (6-Gate Decision)
   ├─ Student requests nonce
   │   └─ Nonce bound to (session_id, user_id, device_id)
   ├─ Student submits verification with WebAuthn signature
   │   └─ Device registered? (D_t) → ✓
   │   └─ Signature valid? (K_t) → ✓
   │   └─ Nonce fresh? (N_t) → ✓
   │   └─ Biometric liveness pass? (B_t) → ✓
   │   └─ Spatial confidence high? (G_t) → ✓
   │   └─ Multi-modal? (M_t) → ✓
   ├─ Decision: A_t = TRUE (all gates passed)
   ├─ Decision stored → attendance_decisions (immutable)
   └─ Attendance marked in class session

6. RESOURCE UNLOCK (Attendance-Gated)
   ├─ [Celery] unlock_resources_for_session starts
   ├─ Query: attendance_decisions where A_t = TRUE
   ├─ For each student with A_t = TRUE:
   │   ├─ Get verified curriculum node IDs for session
   │   ├─ Query resources for those nodes
   │   ├─ Unlock resources → create ProgressiveUnlock event
   │   └─ Log access → curriculum_resource_accesses
   └─ Student can now download materials

7. STUDENT ACCESSES RESOURCES
   ├─ GET /curriculum/resources/{session_id}
   │   └─ Returns: [{resource_id, title, uri, ...}] (only if A_t = TRUE)
   ├─ GET /curriculum/download/{resource_id}
   │   └─ Returns: File stream
   │   └─ Logs: access event (user_id, resource_id, bytes_transferred)
   └─ Access audit trail preserved (90-day TTL)
```

### Guardrails at Each Stage

#### Stage 1: Curriculum Pipeline

```
🔒 Local Processing: No cloud APIs allowed (Ollama, sentence-transformers)
🔒 Threshold Filtering: Only verified mappings used for unlock
🔒 Faculty Review: Immutable verification decisions
🔒 Formula Versioning: s_j formula stored with each mapping
```

#### Stage 2: Attendance Verification

```
🔒 6-Gate Hard AND: All gates must pass (no bypass)
🔒 Device Binding: WebAuthn + clone detection (counter check)
🔒 Biometric Privacy: Outcome-only storage (no raw data)
🔒 Nonce Binding: Single-use, short-lived (5 min), triplet validation
🔒 Immutable Decisions: No modification after attendance_marked=true
```

#### Stage 3: Resource Unlock

```
🔒 Attendance Gate: A_t = TRUE required (hard gate)
🔒 Verified Mappings: Only resources for verified nodes unlocked
🔒 Audit Trail: Every access logged with user_id, resource_id, timestamp
🔒 Data Retention: Access logs deleted after 90 days (TTL index)
```

---

## Deployment Architecture

### Local Development

```
┌─────────────────┐
│   Frontend      │ (React SPA on http://localhost:5173)
└────────┬────────┘
         │
┌────────▼────────────┐
│  Backend (FastAPI)  │ (http://localhost:8000)
├─────────────────────┤
│ - 6 bounded contexts
│ - Pydantic validation
│ - Motor async DB
└────────┬────────────┘
         │
    ┌────┴──────────┬────────────┬──────────────┐
    │               │            │              │
┌───▼───┐  ┌───────▼──┐  ┌─────▼────┐  ┌────▼─────┐
│MongoDB│  │ Ollama   │  │ Redis    │  │ FFmpeg  │
│(27017)│  │(11434)   │  │(6379)    │  │(local)  │
└───────┘  └──────────┘  └──────────┘  └─────────┘
```

### Production Deployment (Docker Compose)

```yaml
services:
  frontend:
    image: scholarlab-frontend:latest
    ports: ["80:3000"]
    environment:
      REACT_APP_API_URL: https://api.scholarlab.edu

  backend:
    image: scholarlab-backend:latest
    ports: ["8000:8000"]
    environment:
      MONGODB_URI: mongodb://mongo:27017/scholarlab
      CELERY_BROKER_URL: redis://redis:6379/0
      OLLAMA_URL: http://ollama:11434
      ENVIRONMENT: production
    volumes:
      - curriculum_audio:/tmp/curriculum_audio

  mongodb:
    image: mongo:7.0
    ports: ["27017:27017"]
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes:
      - ollama_models:/root/.ollama

  celery_worker:
    image: scholarlab-backend:latest
    command: celery -A app.jobs.celery_app worker --loglevel=info
    environment:
      MONGODB_URI: mongodb://mongo:27017/scholarlab
      CELERY_BROKER_URL: redis://redis:6379/0

  celery_beat:
    image: scholarlab-backend:latest
    command: celery -A app.jobs.celery_app beat --loglevel=info
    environment:
      MONGODB_URI: mongodb://mongo:27017/scholarlab
      CELERY_BROKER_URL: redis://redis:6379/0
```

### Environment Profiles

**6 Progressive Strictness Levels:**

```python
# dev: Everything enabled, strict=False, low thresholds
#      biometric_confidence_threshold: 0.85
#      geofence_threshold: 0.50

# staging: Stricter validation, higher thresholds
#          biometric_confidence_threshold: 0.92
#          geofence_threshold: 0.65

# pilot: Production-like, but reversible
#        biometric_confidence_threshold: 0.95
#        geofence_threshold: 0.70

# production: Maximum strictness, immutable decisions
#             biometric_confidence_threshold: 0.98
#             geofence_threshold: 0.75
```

---

## Testing Strategy

### Unit Tests

```bash
# Phase 1: Foundation
pytest backend/tests/test_audit_logging.py -v
pytest backend/tests/test_migrations.py -v

# Phase 2: Attendance
pytest backend/tests/test_device_registration.py -v
pytest backend/tests/test_biometric_liveness.py -v
pytest backend/tests/test_spatial_fusion.py -v
pytest backend/tests/test_attendance_decision.py -v

# Phase 3: Curriculum
pytest backend/tests/test_topic_extraction.py -v
pytest backend/tests/test_syllabus_matching.py -v
pytest backend/tests/test_verification_agent.py -v
pytest backend/tests/test_resource_unlock.py -v
```

### Integration Tests

```bash
# End-to-end: Audio → Attendance → Resources
pytest backend/tests/integration/test_full_pipeline.py -v
```

### Load Testing

```bash
# Locust: Simulate 100 concurrent students checking in
locust -f backend/tests/load_test.py --host=http://localhost:8000 -u 100 -r 10
```

---

## Monitoring & Observability

### Prometheus Metrics

```python
# Curriculum pipeline
curriculum_pipeline_duration_seconds = Histogram(...)
curriculum_topics_extracted = Gauge(...)
curriculum_mappings_below_threshold = Gauge(...)

# Attendance verification
attendance_gates_passed = Counter(...)
attendance_decision_time_seconds = Histogram(...)
biometric_confidence_distribution = Histogram(...)

# Resource unlock
resources_unlocked_per_session = Gauge(...)
resource_access_failures = Counter(...)
```

### Alert Rules

```yaml
- alert: CurriculumTranscriptionFailure
  condition: curriculum_pipeline_errors{stage="transcription"} > 0
  for: 1m
  action: page_oncall

- alert: HighAttendanceDecisionLatency
  condition: attendance_decision_time_seconds{quantile="0.95"} > 5
  for: 5m
  action: warn_team

- alert: VerificationQueueBacklog
  condition: curriculum_verification_pending_tasks > 100
  for: 1h
  action: notify_faculty
```

### Logging

```
[2025-05-21T10:42:00Z] INFO  Curriculum pipeline started for sess_12345
[2025-05-21T10:42:05Z] INFO  ✓ Transcription: 5000 chars, 30s inference
[2025-05-21T10:42:10Z] INFO  ✓ Topics extracted: 15 candidates
[2025-05-21T10:42:25Z] INFO  ✓ Mappings complete: 45 total, 12 below threshold
[2025-05-21T10:42:26Z] INFO  ✓ Verification tasks created: 12 pending

[2025-05-21T10:45:00Z] INFO  Student checked in: student_42
[2025-05-21T10:45:01Z] INFO  ✓ Gate D_t (device): pass
[2025-05-21T10:45:01Z] INFO  ✓ Gate K_t (crypto): pass
[2025-05-21T10:45:01Z] INFO  ✓ Gate M_t (multi-modal): pass
[2025-05-21T10:45:01Z] INFO  ✓ Gate N_t (nonce): pass
[2025-05-21T10:45:01Z] INFO  ✓ Gate B_t (biometric): pass (confidence=0.96)
[2025-05-21T10:45:01Z] INFO  ✓ Gate G_t (geofence): pass (confidence=0.82)
[2025-05-21T10:45:02Z] INFO  ✓ Decision: A_t = TRUE (6/6 gates passed)

[2025-05-21T10:45:30Z] INFO  Progressive unlock started for sess_12345
[2025-05-21T10:45:45Z] INFO  ✓ Unlocked 126 resources for 42 students
```

---

## Security Considerations

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Device Cloning | WebAuthn counter check (hardware counter increments) |
| Biometric Spoofing | Liveness detection (optical flow, temporal consistency) |
| Nonce Replay | Single-use nonce, deleted after validation |
| Attendance Bypass | Hard AND gate (all 6 must pass, no override) |
| Unauthorized Resource Access | A_t = TRUE gate (attendance required) |
| Data Breaches | Outcome-only storage (not raw biometric/location) |
| Audit Tampering | Merkle chains (tamper-evident) |

### Rate Limiting

```python
# Device: max 20 nonce requests per hour
# Biometric: max 10 verification attempts per hour
# API: 1000 req/min per authenticated user
```

### Encryption

```
In Transit: TLS 1.3 (https)
At Rest: MongoDB encryption (AES-256)
Sensitive Fields: Base64 + AES for WebAuthn credentials
```

---

## References

- **SKILL.md:** Production rules (zero-trust, privacy, data integrity, explainability)
- **ATTENDANCE_VERIFICATION_COMPLETE.md:** Phase 2 detailed implementation
- **CURRICULUM_PIPELINE_COMPLETE.md:** Phase 3 detailed implementation
- **docker-compose.yml:** Local development setup
- **DEVELOPMENT_SETUP.md:** Environment configuration

---

## Glossary

| Term | Definition |
|------|-----------|
| **A_t** | Attendance decision at time t (True/False from 6-gate engine) |
| **δ (delta)** | Confidence threshold for syllabus matching (default: 0.6) |
| **s_j** | Cosine similarity between topic and syllabus node j |
| **E(T_t)** | Embedding of extracted topic T_t |
| **C_t** | Composite spatial confidence (weighted sum of 6 signals) |
| **TTL** | Time-to-live (auto-delete after N seconds) |
| **Merkle Chain** | Cryptographic chain where each entry hashes previous entry |
| **WebAuthn** | Web Authentication standard for credential binding |
| **Ollama** | Local LLM framework for running Whisper, embeddings locally |
| **sentence-transformers** | Library for computing sentence embeddings locally |

---

## Version History

| Version | Date | Phase | Changes |
|---------|------|-------|---------|
| 1.0 | 2025-05-21 | All | Initial complete system (P1+P2+P3) |

---

## Next Steps (Future Phases)

**Phase 4: Advanced Analytics**
- Risk scoring (XGBoost with SHAP)
- Predictive intervention (who will drop out?)
- Learning outcome correlation

**Phase 5: Multi-Modal Verification**
- Voice biometric (speaker verification)
- Keystroke dynamics
- Behavioral profiling

**Phase 6: Federated Learning**
- Distributed model training across institutions
- Privacy-preserving aggregation
- Zero-knowledge proofs

---

## Support & Questions

For implementation questions, refer to:
1. **SKILL.md** - Production rules & checklists
2. **ATTENDANCE_VERIFICATION_COMPLETE.md** - Attendance details
3. **CURRICULUM_PIPELINE_COMPLETE.md** - Curriculum details
4. Code comments (inline documentation)
5. Unit/integration tests (usage examples)
