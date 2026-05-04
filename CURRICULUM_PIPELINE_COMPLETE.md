# Curriculum Pipeline: Complete Implementation

## Overview

**Phase 3** of ScholarLab implements a **privacy-preserving multi-agent curriculum pipeline** that:
1. Transcribes lecture audio **locally** (NO cloud APIs)
2. Extracts topics from transcription (keywords, phrases, clustering)
3. Maps topics to curriculum syllabus using **cosine similarity** (s_j formula)
4. Flags low-confidence mappings for **faculty manual verification**
5. Progressively unlocks resources based on **attendance verification** (A_t gate)

### Key Privacy Guarantee
> **ZERO cloud API calls.** All audio processing, embeddings, and inference happen on-device using Ollama and sentence-transformers.

---

## Architecture

### 4 ML Services (Local)

```
Audio File
    ↓
[1. LocalWhisperService]  ← Ollama (local inference)
    ↓ Transcription
Transcript Text
    ↓
[2. TopicExtractionService]  ← TF-IDF + n-grams + clustering
    ↓ CandidateTopic[]
Topic List
    ↓
[3. SyllabusMatchingAgent]  ← sentence-transformers + cosine similarity
    ↓ TopicMappingResult (with s_j scores)
Mappings (above & below δ threshold)
    ↓
[4. VerificationAgent]  ← Faculty manual review
    ↓ VerificationTask[]
Verified Mappings
    ↓
[5. ResourceUnlockService]  ← Attendance-gated (A_t = True)
    ↓
Student URIs unlocked
```

### End-to-End Integration

**Orchestration:** Celery `curriculum_pipeline()` task chains all 5 services:
1. Transcribe audio
2. Extract topics
3. Match to syllabus (compute embeddings, filter by δ)
4. Create verification tasks (below_threshold)
5. Faculty reviews & approves (via API endpoint)
6. Resources unlocked when A_t = True

---

## Detailed Component Reference

### Service 1: LocalWhisperService (Transcription)

**File:** `backend/app/ml/local_whisper.py` (~300 lines)

**Purpose:** Convert audio → text via local Ollama Whisper model.

**Key Methods:**
- `transcribe_audio(audio_file_path, session_id)` → TranscriptionResult
- `_convert_to_wav(input_path)` → 16kHz WAV (ffmpeg)
- `_get_audio_duration(audio_path)` → seconds

**Model:**
```python
class TranscriptionResult:
    session_id: str
    transcript: str
    segments: List[TranscriptionSegment]  # {start_time, end_time, text, confidence}
    language: str
    duration_seconds: float
    inference_time_seconds: float
```

**Requirements:**
- Ollama running locally: `ollama serve`
- Whisper model downloaded: `ollama pull whisper`
- ffmpeg installed: `apt install ffmpeg`
- ffprobe (bundled with ffmpeg)

**Privacy:** No API calls. All inference local.

---

### Service 2: TopicExtractionService (NLP)

**File:** `backend/app/ml/topic_extraction.py` (~280 lines)

**Purpose:** Extract candidate topics from transcript using NLP.

**Key Methods:**
- `extract_keywords()` → dict {keyword: frequency}
- `extract_phrases()` → bigrams/trigrams
- `extract_topics()` → ranked CandidateTopic[] with deduplication

**Algorithm:**
1. **Keywords:** TF-based with 108 English stopwords
2. **Phrases:** Bigrams + trigrams (2-3 word sequences)
3. **Clustering:** Merge substrings (e.g., "machine learning" ⊆ "machine learning models")
4. **Confidence:** min(1.0, frequency / 10)
5. **Ranking:** By frequency × confidence

**Model:**
```python
class CandidateTopic:
    topic: str
    frequency: int
    confidence: float  # [0, 1]
    source: str  # "keyword" | "phrase" | "cluster"

class TopicExtractionResult:
    session_id: str
    candidates: List[CandidateTopic]
    transcript_length: int
    extracted_at: datetime
```

**Privacy:** Pure local processing. No external APIs.

---

### Service 3: SyllabusMatchingAgent (Embeddings + Similarity)

**File:** `backend/app/services/syllabus_matcher.py` (~400 lines)

**Purpose:** Match extracted topics to curriculum nodes using cosine similarity.

**Formula:**
$$s_j = \cos(E(T_t), e_j) = \frac{E(T_t) \cdot e_j}{||E(T_t)|| \cdot ||e_j||}$$

Where:
- $E(T_t)$ = embedding of extracted topic
- $e_j$ = embedding of curriculum node j
- $s_j \in [0, 1]$ = similarity score

**Key Methods:**
- `match_topics_to_nodes()` → TopicMappingResult (orchestrator)
- `_load_curriculum_tree()` → SyllabusNode[]
- `_get_node_embedding()` → with caching to DB
- `filter_by_confidence(mapping, δ)` → (above_threshold, below_threshold)

**Embedding Model:**
- **all-MiniLM-L6-v2** (sentence-transformers)
- **Dimensions:** 384-dimensional vectors
- **Size:** ~22 MB (downloaded once, cached locally)
- **Speed:** ~50ms per text

**Caching Strategy:**
- Embeddings cached in MongoDB collection: `curriculum_node_embeddings_cache`
- Indexed by `node_id` (unique)
- Check cache → compute if missing → store
- Avoids re-computing for repeat queries

**Models:**
```python
class TopicMappingResult:
    session_id: str
    course_id: str
    extracted_topics_count: int
    mapped_topics_count: int
    total_matches: int
    matches: List[SyllabusNodeMatch]
    below_threshold_count: int
    confidence_threshold: float  # δ (delta)

class SyllabusNodeMatch:
    topic: str
    topic_confidence: float  # From extraction
    curriculum_node_id: str
    node_title: str
    similarity_score: float  # s_j
    rank: int  # Rank among matches for this topic
```

**Workflow:**
1. Load all curriculum nodes for course
2. Precompute embeddings (batch) → cache
3. For each extracted topic:
   - Embed topic
   - Compute cosine similarity vs all nodes
   - Sort by s_j (descending)
   - Take top-3 matches
4. Filter by threshold δ (default: 0.6)
5. Flag below-threshold for verification

**Privacy:** sentence-transformers runs locally. No API calls.

---

### Service 4: VerificationAgent (Faculty Review)

**File:** `backend/app/services/verification_agent.py` (~550 lines)

**Purpose:** Create manual review workflow for low-confidence mappings.

**Workflow:**
1. Identify mappings where $s_j < δ$ (below confidence threshold)
2. Create VerificationTask for each
3. Faculty reviews curriculum and confirms/rejects/corrects
4. Store decision → trigger resource unlock

**Task Lifecycle:**
```
PENDING → APPROVED       (faculty confirmed)
       → REJECTED        (faculty rejected)
       → CORRECTED       (faculty provided correct mapping)
```

**Key Methods:**
- `create_verification_tasks()` → VerificationTask[]
- `approve_mapping(task_id, faculty_id)` → VerificationResult
- `reject_mapping(task_id, faculty_id, reason)`
- `correct_mapping(task_id, correct_node_id, faculty_id)`
- `get_pending_tasks(course_id, faculty_id)` → VerificationTask[]

**Models:**
```python
class VerificationTask:
    task_id: str
    session_id: str
    course_id: str
    topic: str
    topic_confidence: float
    original_node_id: str
    original_node_title: str
    similarity_score: float  # s_j
    status: VerificationStatus  # pending | approved | rejected | corrected
    faculty_id: Optional[str]
    verified_at: Optional[datetime]
    corrected_node_id: Optional[str]  # If corrected
    corrected_node_title: Optional[str]
    notes: Optional[str]

class VerificationResult:
    task_id: str
    original_mapping: SyllabusNodeMatch
    corrected_mapping: Optional[SyllabusNodeMatch]  # If corrected
    verification_status: VerificationStatus
    faculty_id: str
    verified_at: datetime
```

**Analytics:**
- `get_session_verification_status()` → BulkVerificationStatus (completion rate)
- `get_faculty_workload()` → stats by faculty

---

### Service 5: ResourceUnlockService (Attendance-Gated)

**File:** `backend/app/services/resource_unlock.py` (~450 lines)

**Purpose:** Progressively unlock curriculum resources based on attendance.

**Gate Equation:**
$$\text{Resource Unlock} = A_t$$

If $A_t = \text{True}$ (student verified present) → Resources unlocked
If $A_t = \text{False}$ → Resources remain locked

**Resource Types:**
- `LECTURE_NOTES` (PDF, markdown)
- `SLIDES` (presentations)
- `RECORDINGS` (session video)
- `SUPPLEMENTARY` (additional materials)
- `ASSIGNMENTS` (homework)
- `SOLUTIONS` (answer keys)

**Key Methods:**
- `unlock_resources_for_student(user_id, session_id, attendance_verified, curriculum_node_ids)` → ProgressiveUnlock
- `record_resource_download(access_id, bytes_transferred)`
- `get_student_resource_accesses(user_id, session_id)` → ResourceAccess[]

**Models:**
```python
class CurriculumResource:
    resource_id: str
    curriculum_node_id: str
    resource_type: ResourceType
    title: str
    uri: str  # Encrypted URL/path
    requires_attendance: bool  # Must have A_t = True?

class ProgressiveUnlock:
    unlock_id: str
    user_id: str
    session_id: str
    attendance_verified: bool  # A_t
    attendance_decision_id: str
    resource_ids: List[str]
    curriculum_node_ids: Set[str]
    unlock_count: int
    unlocked_at: datetime

class ResourceAccess:
    access_id: str
    user_id: str
    resource_id: str
    session_id: str
    attendance_verified: bool
    accessed_at: datetime
    bytes_transferred: Optional[int]  # For audit
```

**Audit Trail:**
- Every access logged to `curriculum_resource_accesses`
- TTL: 90 days (auto-cleanup)
- Tracks: user, resource, session, time, bytes
- Can answer: "Did student download slides?"

---

## End-to-End Workflow

### Step 1: Faculty Uploads Audio (Manual)

```
Faculty records 60-minute lecture → uploads MP3/WAV/M4A file
System stores in `/tmp/curriculum_audio/{session_id}.mp3`
Faculty clicks: "Process Lecture Recording"
```

### Step 2: Celery Task Chains All Services

**Task:** `curriculum_pipeline(session_id, course_id, audio_file_path)`

```
[Celery Task Timeline]

T=0s     Transcribe audio (Ollama)
         ├─ Convert to 16kHz WAV
         ├─ Call Ollama locally
         └─ T=30s: Transcript ready

T=30s    Extract topics
         ├─ TF-IDF + n-grams
         ├─ Dedup clusters
         └─ T=35s: 15 topics extracted

T=35s    Syllabus matching
         ├─ Embed 15 topics
         ├─ Query 500 curriculum nodes
         ├─ Compute cosine similarity (500×15)
         └─ T=50s: 45 mappings found (3 per topic)

T=50s    Verification tasks
         ├─ Filter: s_j < 0.6 → 12 below threshold
         ├─ Create 12 verification tasks
         └─ T=51s: Tasks queued for faculty

T=51s    Return result to API
{
  "session_id": "sess_12345",
  "topics_extracted": 15,
  "mapped_topics": 15,
  "total_matches": 45,
  "below_threshold": 12,
  "verification_tasks_created": 12,
  "completed_at": "2025-05-21T10:42:15Z"
}
```

### Step 3: Faculty Reviews Low-Confidence Mappings

**API Endpoint:** `GET /curriculum/verification-queue?course_id=CS101`

Faculty sees:
```json
{
  "pending_tasks": 12,
  "tasks": [
    {
      "task_id": "verify_789",
      "topic": "machine learning",
      "topic_confidence": 0.85,
      "original_node": "Module 5 > Advanced ML",
      "similarity_score": 0.58,  // Below δ=0.6
      "status": "pending"
    },
    { ... }
  ]
}
```

Faculty reviews each and:
- **Approve:** "Yes, topic matches this node" → s_j becomes 1.0 (verified)
- **Reject:** "No, wrong mapping" → removed from curriculum
- **Correct:** "Actually, it's this other node" → corrected_node_id stored

**API Endpoint:** `POST /curriculum/verify/{task_id}`

```json
{
  "action": "approve",  // "approve" | "reject" | "correct"
  "faculty_id": "prof_alice",
  "notes": "Confirmed covers ML basics",
  "corrected_node_id": null  // Only if action="correct"
}
```

### Step 4: Resources Automatically Unlock (After Attendance)

**Trigger:** Student successfully checks into session (A_t = True)

**Celery Task:** `unlock_resources_for_session(session_id, course_id, verified_node_ids)`

For each student with A_t = True:
```python
unlock_result = await resource_unlock_svc.unlock_resources_for_student(
    user_id="student_42",
    session_id="sess_12345",
    course_id="CS101",
    attendance_verified=True,  # A_t
    attendance_decision_id="decision_999",
    curriculum_node_ids=[
        "node_001",  # Machine Learning (verified mapping)
        "node_002",  # Neural Networks (verified mapping)
        "node_003",  # etc.
    ]
)
```

Returns:
```python
ProgressiveUnlock(
    unlock_id="unlock_aaa",
    user_id="student_42",
    session_id="sess_12345",
    attendance_verified=True,
    resource_ids=[
        "res_001",  # Slides PDF
        "res_002",  # Lecture notes
        "res_003",  # Session recording
    ],
    unlock_count=3,
)
```

### Step 5: Student Accesses Resources

**API Endpoint:** `GET /curriculum/resources/{session_id}`

Student sees:
```json
{
  "unlocked_resources": [
    {
      "resource_id": "res_001",
      "title": "Lecture Slides - Machine Learning Intro",
      "resource_type": "slides",
      "uri": "/api/download/res_001?token=...",
      "attendance_verified": true
    },
    { ... }
  ]
}
```

**Access Log:**
- Every download recorded to `curriculum_resource_accesses`
- Includes: user_id, resource_id, session_id, timestamp, bytes_transferred
- Auto-deleted after 90 days (TTL index)

---

## Database Schema (7 New Collections)

### 1. `curriculum_topic_mappings`

Topic extraction → syllabus matching results

```json
{
  "_id": ObjectId,
  "session_id": "sess_12345",
  "course_id": "CS101",
  "extracted_topics_count": 15,
  "mapped_topics_count": 15,
  "total_matches": 45,
  "below_threshold_count": 12,
  "matches": [
    {
      "topic": "machine learning",
      "topic_confidence": 0.85,
      "curriculum_node_id": "node_001",
      "node_title": "Module 5 > Advanced ML",
      "similarity_score": 0.72,
      "rank": 1
    }
  ],
  "confidence_threshold": 0.6,
  "created_at": ISODate("2025-05-21T10:42:00Z")
}
```

**Indexes:**
- session_id
- course_id
- topic
- created_at

---

### 2. `curriculum_node_embeddings_cache`

Precomputed 384-dimensional embeddings (sentence-transformers)

```json
{
  "_id": ObjectId,
  "node_id": "node_001",
  "course_id": "CS101",
  "embedding": [0.123, -0.456, ..., 0.789],  // 384 floats
  "cached_at": ISODate("2025-05-21T10:30:00Z")
}
```

**Indexes:**
- node_id (unique)
- course_id

---

### 3. `curriculum_verification_tasks`

Faculty manual review queue

```json
{
  "_id": ObjectId,
  "task_id": "verify_789",
  "session_id": "sess_12345",
  "course_id": "CS101",
  "topic": "machine learning",
  "topic_confidence": 0.85,
  "original_node_id": "node_001",
  "original_node_title": "Module 5",
  "similarity_score": 0.58,
  "status": "pending",  // pending | approved | rejected | corrected
  "faculty_id": null,
  "verified_at": null,
  "corrected_node_id": null,
  "corrected_node_title": null,
  "notes": null,
  "created_at": ISODate("2025-05-21T10:42:10Z")
}
```

**Indexes:**
- task_id (unique)
- session_id
- course_id
- status
- faculty_id
- created_at

---

### 4. `curriculum_verified_mappings`

Faculty decisions (approved, rejected, or corrected)

```json
{
  "_id": ObjectId,
  "task_id": "verify_789",
  "session_id": "sess_12345",
  "verification_status": "approved",
  "original_mapping": {
    "topic": "machine learning",
    "similarity_score": 0.58,
    "curriculum_node_id": "node_001"
  },
  "corrected_mapping": null,
  "faculty_id": "prof_alice",
  "verified_at": ISODate("2025-05-21T11:15:00Z"),
  "notes": "Confirmed matches module content"
}
```

**Indexes:**
- session_id
- course_id
- task_id

---

### 5. `curriculum_resources`

Lecture materials (notes, slides, recordings, etc.)

```json
{
  "_id": ObjectId,
  "resource_id": "res_001",
  "curriculum_node_id": "node_001",
  "resource_type": "slides",
  "title": "Lecture Slides - ML Intro",
  "description": "Introduction to machine learning concepts",
  "uri": "s3://scholarlab-curriculum/CS101/module5/slides.pdf",
  "size_bytes": 2500000,
  "requires_attendance": true,
  "created_at": ISODate("2025-05-21T08:00:00Z")
}
```

**Indexes:**
- curriculum_node_id
- resource_type
- requires_attendance

---

### 6. `curriculum_resource_accesses`

Audit trail: who accessed what resource when

```json
{
  "_id": ObjectId,
  "access_id": "access_123",
  "user_id": "student_42",
  "resource_id": "res_001",
  "session_id": "sess_12345",
  "curriculum_node_id": "node_001",
  "resource_type": "slides",
  "attendance_verified": true,
  "attendance_decision_id": "decision_999",
  "accessed_at": ISODate("2025-05-21T11:20:00Z"),
  "ip_address": "192.168.1.42",
  "bytes_transferred": 2500000
}
```

**Indexes:**
- user_id
- resource_id
- session_id
- accessed_at
- **TTL index on accessed_at (90 days)**: Auto-cleanup

---

### 7. `curriculum_progressive_unlocks`

When resources are unlocked for students (attendance-gated events)

```json
{
  "_id": ObjectId,
  "unlock_id": "unlock_aaa",
  "user_id": "student_42",
  "session_id": "sess_12345",
  "course_id": "CS101",
  "attendance_verified": true,
  "attendance_decision_id": "decision_999",
  "resource_ids": ["res_001", "res_002", "res_003"],
  "curriculum_node_ids_list": ["node_001", "node_002"],
  "unlock_count": 3,
  "unlocked_at": ISODate("2025-05-21T10:52:00Z")
}
```

**Indexes:**
- user_id
- session_id
- unlocked_at

---

## Celery Tasks

### Task 1: `curriculum_pipeline`

**Endpoint:** POST `/curriculum/sessions/{session_id}/process-audio`

```python
curriculum_pipeline.delay(
    session_id="sess_12345",
    course_id="CS101",
    audio_file_path="/tmp/curriculum_audio/sess_12345.mp3",
)
```

**Chaining:**
1. Transcribe (LocalWhisperService)
2. Extract topics (TopicExtractionService)
3. Match to syllabus (SyllabusMatchingAgent)
4. Create verification tasks (VerificationAgent)

**Result:**
```json
{
  "session_id": "sess_12345",
  "stage": "verification_needed",
  "topics_extracted": 15,
  "mapped_topics": 15,
  "total_matches": 45,
  "below_threshold": 12,
  "verification_tasks_created": 12
}
```

### Task 2: `unlock_resources_for_session`

**Called After:** Attendance verification completes

```python
unlock_resources_for_session.delay(
    session_id="sess_12345",
    course_id="CS101",
    verified_curriculum_node_ids=["node_001", "node_002", "node_003"],
)
```

**Process:**
1. Query attendance decisions: A_t = True
2. For each student: unlock resources for verified nodes
3. Log unlock events

**Result:**
```json
{
  "session_id": "sess_12345",
  "students_with_attendance": 42,
  "resources_unlocked": 126,
  "total_unlock_events": 42
}
```

---

## API Endpoints (Routes)

**File:** `backend/app/routers/curriculum_pipeline.py` (to be created)

### 1. POST `/curriculum/sessions/{session_id}/process-audio`

Faculty uploads lecture recording for processing.

```python
@router.post("/sessions/{session_id}/process-audio")
async def process_lecture_audio(
    session_id: str,
    course_id: str,
    file: UploadFile,
    current_user: User = Depends(get_current_user),  # faculty role
):
    """Queue curriculum pipeline task."""
    # Save file
    # Call curriculum_pipeline.delay(...)
    # Return task_id
```

### 2. GET `/curriculum/sessions/{session_id}/audio-status`

Check processing status.

```python
@router.get("/sessions/{session_id}/audio-status")
async def get_audio_processing_status(session_id: str):
    """Get Celery task status."""
    # Return: {task_id, state, progress, result}
```

### 3. GET `/curriculum/mappings/{session_id}`

Retrieve all topic→node mappings for session.

```python
@router.get("/mappings/{session_id}")
async def get_topic_mappings(session_id: str):
    """Get TopicMappingResult with all matches."""
```

### 4. GET `/curriculum/verification-queue`

Faculty views pending verification tasks.

```python
@router.get("/verification-queue")
async def get_verification_queue(
    course_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),  # faculty role
):
    """Get list of VerificationTask (status=pending)."""
```

### 5. POST `/curriculum/verify/{task_id}`

Faculty confirms/rejects/corrects a mapping.

```python
@router.post("/verify/{task_id}")
async def verify_mapping(
    task_id: str,
    action: Literal["approve", "reject", "correct"],
    faculty_id: str,
    corrected_node_id: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),  # faculty role
):
    """Record faculty decision."""
```

### 6. GET `/curriculum/resources/{session_id}`

Student retrieves unlocked resources (attendance-gated).

```python
@router.get("/resources/{session_id}")
async def get_unlocked_resources(
    session_id: str,
    current_user: User = Depends(get_current_user),  # student role
):
    """
    Return list of unlocked resources if A_t = True.
    Otherwise, empty list.
    """
```

### 7. GET `/curriculum/download/{resource_id}`

Student downloads resource (with audit logging).

```python
@router.get("/download/{resource_id}")
async def download_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),  # student role
):
    """
    Stream resource file.
    Log access (user, resource, timestamp, bytes).
    """
```

---

## Testing & Validation

### Unit Tests

```bash
pytest backend/tests/test_curriculum_pipeline.py -v
```

**Test Cases:**
1. Transcription: audio → transcript
2. Topic extraction: transcript → topics
3. Syllabus matching: topics → nodes (cosine similarity)
4. Verification: below-threshold tasks created
5. Resource unlock: attendance-gated unlock events
6. API endpoints: CRUD operations

### Integration Tests

```bash
# 1. Upload audio file
curl -X POST http://localhost:8000/curriculum/sessions/sess_test/process-audio \
  -F "file=@lecture.mp3" \
  -H "Authorization: Bearer $FACULTY_TOKEN"

# 2. Check status
curl http://localhost:8000/curriculum/sessions/sess_test/audio-status \
  -H "Authorization: Bearer $FACULTY_TOKEN"

# 3. View verification queue
curl http://localhost:8000/curriculum/verification-queue \
  -H "Authorization: Bearer $FACULTY_TOKEN"

# 4. Approve a mapping
curl -X POST http://localhost:8000/curriculum/verify/verify_789 \
  -H "Authorization: Bearer $FACULTY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "notes": "Confirmed"}'

# 5. Student views unlocked resources
curl http://localhost:8000/curriculum/resources/sess_test \
  -H "Authorization: Bearer $STUDENT_TOKEN"

# 6. Download resource
curl http://localhost:8000/curriculum/download/res_001 \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -o lecture_slides.pdf
```

---

## Performance Considerations

### Bottlenecks & Optimization

| Component | Bottleneck | Mitigation |
|-----------|-----------|-----------|
| Transcription | Ollama inference time | Batch multiple sessions, async processing |
| Embeddings | Computing 500+ nodes | Precompute + cache in MongoDB |
| Cosine similarity | 15 topics × 500 nodes | Vectorized NumPy operations, filter by top-k |
| Verification | Faculty manual review | Parallel task assignment to multiple faculty |
| Resource unlock | Database writes | Batch inserts, parallel unlock per student |

### Resource Requirements

**Local Infrastructure:**
- Ollama + Whisper model: 1 GPU (A10, L4, or better)
- sentence-transformers: 1 CPU core, 2 GB RAM
- MongoDB: 10 GB (curriculum + events)
- Redis (Celery): 1 GB
- Disk: 50 GB (audio files, embeddings cache)

**Example Hardware:**
```
CPU: 8-core
GPU: NVIDIA A10 (24 GB)
RAM: 32 GB
Storage: 500 GB SSD
```

---

## Privacy Guarantees

### Zero-Trust for Curriculum

1. **No Cloud APIs:**
   - ✅ Ollama (local Whisper, not cloud transcription)
   - ✅ sentence-transformers (local embeddings, not HuggingFace API)
   - ✅ FFmpeg (local audio conversion)

2. **No Raw Data Storage:**
   - Audio: Transcribed → deleted
   - Biometrics: Outcome only (not stored)
   - Location: Signal-only (not raw coordinates)

3. **Audit Trail:**
   - Every resource access logged
   - Faculty decisions immutable
   - Attendance decisions immutable

4. **Attendance-Gated:**
   - Resources unlock **only if A_t = True**
   - No exception bypass (hard gate)
   - Prevents unauthorized access

---

## Data Integrity Checks

### Formula Versioning (Cosine Similarity)

```json
{
  "session_id": "sess_12345",
  "similarity_formula_version": "v1.0",
  "formula": "s_j = (E(T_t) · e_j) / (||E(T_t)|| * ||e_j||)",
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_model_version": "2.12",
  "cosine_implementation": "NumPy",
  "threshold_delta": 0.6
}
```

This enables:
- Reproducibility
- Explainability
- Audit trail of formula changes
- Recomputation if needed

---

## Explainability: SHAP for Curriculum

Optional: Explain **why** a topic matched a node.

```python
# SHAP decomposition of s_j
top_terms_in_topic = ["machine", "learning", "algorithm"]
top_terms_in_node = ["machine", "learning", "neural"]

# Shared terms contribute most to similarity
contribution = {
    "machine": 0.35,
    "learning": 0.32,
    "algorithm": 0.18,
    "neural": 0.15,  # Only in node, slight contribution
}

shap_summary = f"High similarity (s_j=0.72) driven by shared terms: {top_shared}"
```

---

## Monitoring & Alerts

### Metrics to Track

```python
prometheus_metrics = {
    "curriculum_pipeline_duration_seconds": histogram,
    "curriculum_topics_extracted_per_session": gauge,
    "curriculum_mappings_below_threshold": gauge,
    "curriculum_verification_pending_tasks": gauge,
    "curriculum_resources_unlocked_per_session": gauge,
    "curriculum_access_failures": counter,
}
```

### Alert Rules

```yaml
- alert: CurriculumTranscriptionFailed
  condition: curriculum_pipeline_errors > 0
  threshold: 1 failure

- alert: HighVerificationBacklog
  condition: curriculum_verification_pending_tasks > 50
  threshold: 50 tasks

- alert: ResourceUnlockLatency
  condition: curriculum_unlock_duration_seconds > 30
  threshold: 30 seconds
```

---

## FAQ

**Q: What if Ollama is not available?**
A: Graceful degradation → return 503 Service Unavailable. Faculty can retry after service recovery.

**Q: Can faculty override the cosine similarity threshold δ?**
A: No. δ=0.6 is hardcoded (production rules). Faculty reviews below-threshold but cannot change gate.

**Q: What happens if A_t = False?**
A: Resources remain locked. Student can retry attendance verification (device registration, biometric, etc.).

**Q: Can students access resources without attending class?**
A: No. A_t = True is a hard gate. No API bypass or override.

**Q: How long are resources unlocked?**
A: Indefinitely until course ends (or resource deleted). Faculty can revoke via API if needed.

**Q: Can faculty correct mappings after verification?**
A: Yes. API allows POST /curriculum/verify/{task_id} with action="correct" to change mapping.

---

## References

- **Phase 1:** Production Rules (SKILL.md)
- **Phase 2:** Attendance Verification (ATTENDANCE_VERIFICATION_COMPLETE.md)
- **Phase 3:** Curriculum Pipeline (this document)
