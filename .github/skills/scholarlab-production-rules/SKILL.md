---
name: scholarlab-production-rules
description: 'Production rules for ScholarLab stack (React SPA, FastAPI, MongoDB). Use when: implementing attendance/verification features, designing authentication, handling biometric/location data, generating seed data, or building ML features. Enforces zero-trust validation, privacy-preserving inference, data integrity, and explainability.'
user-invocable: false
disable-model-invocation: false
---

# ScholarLab Production Rules

**Stack**: React (SPA) → Node.js/Express (Auth/Middleware) → FastAPI (Analytics/Curriculum) → MongoDB  
**Identity Model**: Student, Faculty, Admin, Device, Session, Room, Badge  
**Event Model**: Immutable, append-only logs for attendance, syllabus mapping, risk, overrides, audits

---

## 1. Zero-Trust Architecture

**Principle**: Never trust a single signal. All attendance decisions require **multi-modal validation** (Device + Biometric + Spatial).

### Checklist

- [ ] **Attendance Entry**: Require ALL three signals before marking attendance
  - Device verification (registered device + session token)
  - Biometric confirmation (face, fingerprint, or WebAuthn challenge)
  - Spatial validation (geofence within 10m radius + room beacon confirmation)
  
- [ ] **Risk Scoring**: Cross-validate signals for anomaly detection
  - Device: Check for historical patterns (time, location, frequency)
  - Biometric: Verify confidence score > 0.95 for face recognition
  - Spatial: Confirm room occupancy via beacon/WiFi triangulation
  
- [ ] **Session Lifecycle**: Enforce multi-modal checks on sensitive operations
  - Login: Device ID + biometric + IP geofence
  - Attendance marking: All three + WebSocket session validation
  - Override (Faculty): Signed audit log + approval chain + biometric re-confirmation
  
- [ ] **Fallback Handling**: If one signal fails
  - ❌ Do NOT accept attendance with only 2/3 signals
  - ✅ Require manual faculty override with audit trail
  - ✅ Log signal failures for forensic analysis
  
- [ ] **Device Trust Model**: Implement certificate pinning
  - Validate device certificate on every WebSocket message
  - Rotate keys quarterly; track rotation in immutable audit log
  - Reject sessions with invalid/expired certificates

---

## 2. Privacy-Preserving Inference

**Principle**: ALL audio transcription and LLM concept extraction **MUST run locally** (e.g., Ollama/LangChain). NEVER send raw classroom audio to public cloud APIs.

### Checklist

- [ ] **Audio Processing Pipeline**
  - ✅ Store raw audio ONLY in encrypted local storage or edge device
  - ✅ Transcribe using local Ollama model (Whisper) or on-device decoder
  - ✅ Extract concepts using local LLM (Ollama, LLaMA 2, Mistral) — NO API calls
  - ❌ Never upload raw audio to AWS Transcribe, Google Speech-to-Text, or Azure Cognitive Services
  
- [ ] **LLM Outputs**: Document lineage for explainability
  - Store prompt templates (prompt → model name → version → output)
  - Include SHAP attribution scores for key phrases
  - Version control all prompt changes in git
  
- [ ] **Data Residency**: Keep PII in ScholarLab infrastructure
  - Syllabus extracts (concepts, learning outcomes)
  - Student risk profiles (aggregate statistics only, never raw audio)
  - Attendance patterns (anonymized or per-student only)
  
- [ ] **Consent & Opt-Out**
  - Implement audio transcription toggle (per-room or per-student)
  - Log all transcription requests in immutable audit log
  - Provide students/parents download of their transcription data
  
- [ ] **Encryption at Rest & In Transit**
  - TLS 1.3 for all API calls
  - MongoDB encryption at rest (ChaCha20-Poly1305 or AES-256-GCM)
  - Ephemeral keys; rotate monthly

---

## 3. Data Integrity

**Principle**: Use ONLY real-world, factual values. Immutable, append-only event logs for all state changes.

### Checklist

- [ ] **Seed Data & Test Datasets**: Real-world values ONLY
  - ✅ Realistic student names, emails, enrollment patterns (match actual institution data)
  - ✅ Valid geofence coordinates (actual campus buildings + 10m buffer)
  - ✅ Plausible curriculum (real courses, learning outcomes, assessment rubrics)
  - ✅ Historical attendance patterns (match typical institution absences ~15%)
  - ❌ Never use placeholder: "John Doe", "test@test.com", "12345 Fake St"
  - ❌ Never fabricate ML training data; use real institution data (de-identified)
  
- [ ] **Database Migrations**: Immutable event logging
  - Every state change = new event log entry (never UPDATE, only INSERT + flag)
  - Schema: `{id, entity_id, entity_type, timestamp, actor, action, old_value, new_value, metadata}`
  - Example: Attendance override → `{action: "override", actor: "faculty_123", old_value: "unmarked", new_value: "marked", reason: "medical"}`
  
- [ ] **Audit Trail**: Append-only, tamper-evident
  - Sign audit logs with faculty/admin public key
  - Include previous log hash (Merkle chain style) to detect tampering
  - Persist in write-once MongoDB collection (capped or immutable)
  
- [ ] **Consistency Checks**: Detect data anomalies
  - Attendance count vs. syllabus enrollment count (alert if > 5% mismatch)
  - Risk score vs. underlying signal data (validate formula reproducibility)
  - Biometric confidence scores (reject if missing or < 0.9 for production)

---

## 4. Explainability

**Principle**: ML models paired with human-readable rolling formulas and SHAP outputs. No black-box predictions.

### Checklist

- [ ] **Risk Scoring Formula**: Publish rolling window calculation
  - **Example**: `risk_score = 0.4 * recent_absence_rate + 0.3 * engagement_score + 0.2 * biometric_anomaly + 0.1 * curriculum_mismatch`
  - Version formula in code comments: `// v2.1: Adjusted weights for Spring 2026 based on SHAP analysis`
  - Log formula used for each student (immutable audit trail)
  
- [ ] **SHAP Attribution**: Every risk prediction includes feature importance
  - Output: `{risk_score: 0.68, shap_values: {absence_rate: +0.25, engagement: -0.10, biometric_anomaly: +0.15, curriculum_gap: +0.08}}`
  - Visualize top 3 contributing factors for faculty/advisor
  - Store SHAP logs for post-hoc audits
  
- [ ] **Model Versioning**: Track all model changes
  - Save XGBoost/RandomForest joblib with metadata: `{model_name, version, training_date, feature_set, performance_metrics}`
  - Include baseline performance: precision, recall, AUC-ROC on held-out test set
  - Comment threshold decisions: `// risk_threshold=0.65 chosen to minimize false positives for low-engagement students`
  
- [ ] **Curriculum Mapping**: Link concepts to learning outcomes
  - Store: `{session_id, concept: "photosynthesis", learning_outcome_id, confidence: 0.87, source: "audio_transcript"}`
  - Allow faculty override: `{concept: "photosynthesis", corrected_outcome: "bio_102_4", reason: "mistranscription"}`
  - Report to students: "Your performance on photosynthesis (87% confidence) aligns with learning outcome X"
  
- [ ] **Fairness & Bias Audits**: Monthly checks
  - Stratify risk scores by student demographics: `{risk_score, gender, first_gen, international, campus_distance}`
  - Alert if Δ risk_score > 10% across groups (same attendance pattern)
  - Document corrective actions in audit log

---

## Design Decision Tree

Use this when evaluating new features or API endpoints:

```
Is this a new attendance/verification feature?
├─ YES → Apply Zero-Trust (1), Audit Trail (3)
│        Ask: What signals validate this? Need all 3?
│
├─ NO: Is this audio/LLM processing?
│      YES → Apply Privacy (2), Explainability (4)
│           Ask: Is local inference possible? If not, justify + get approval
│
├─ NO: Is this generating test data or migrations?
│      YES → Apply Data Integrity (3)
│           Ask: Are values real-world? Can we verify against institution records?
│
└─ NO: Is this an ML feature?
       YES → Apply Explainability (4), Audit Trail (3)
            Ask: Can we explain predictions to faculty/students?
```

---

## Identity & Event Model Reference

### Identity Model
- **Student**: User + Biometric Profile + Device Registry
- **Faculty**: User + Admin Scope (course roster, override keys)
- **Admin**: Audit access + system configuration
- **Device**: Registered phone/laptop + certificate chain + geofence exceptions
- **Session**: WebSocket + token + multi-modal validation history
- **Room**: Building ID + geofence + Bluetooth beacons + occupancy sensors
- **Badge**: Attendance record + override chain + risk annotations

### Event Model (Immutable Logs)
```json
{
  "event_id": "uuid",
  "timestamp": "2026-05-04T14:30:00Z",
  "entity_type": "attendance | override | risk_flag | curriculum_map",
  "entity_id": "student_123 | session_456",
  "actor": "student_123 | faculty_456 | system",
  "action": "mark | override | flag | correct | revoke",
  "signals": {
    "device_valid": true,
    "biometric_confidence": 0.96,
    "geofence_distance": 3.2
  },
  "metadata": {
    "formula_version": "2.1",
    "ml_model_version": "xgboost_v1.3",
    "previous_event_hash": "sha256..."
  }
}
```

---

## Common Pitfalls

❌ **Attendance without multi-modal validation** → Request rejected by security middleware  
❌ **Uploading audio to cloud APIs** → Privacy breach; violate FERPA/local data protection laws  
❌ **Using fake test data** → Risk model trained on unrealistic patterns; poor generalization  
❌ **ML predictions without SHAP** → Unexplainable to faculty; prone to bias complaints  
❌ **No audit trail for overrides** → Can't prove who changed what; compliance failure  

---

## When to Consult This Skill

- **Code Review**: Verify new attendance/auth endpoints meet zero-trust criteria
- **Feature Design**: Brainstorm what signals a new feature needs
- **Testing**: Generate realistic seed data; validate immutable logs
- **Compliance**: Prepare for audits; prove privacy/fairness controls
- **Debugging**: Trace a risk score back to its formula and SHAP values
