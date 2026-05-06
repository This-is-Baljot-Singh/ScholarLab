# ScholarLab: Comprehensive Documentation

## 1. Project Overview
**ScholarLab** is a production-grade, end-to-end platform designed for educational institutions to manage student attendance through a **Zero-Trust Verification Pipeline** and synchronize it with a dynamic **Curriculum Knowledge Graph**. It integrates advanced cryptographic verification, spatial geofencing, and machine learning to eliminate attendance spoofing while providing real-time analytics for faculty.

---

## 2. Technology Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) for high-performance asynchronous API services.
- **Database**: 
  - **MongoDB**: Primary store for unstructured/semi-structured data (Attendance, Curriculum, Geofences).
  - **Redis**: Used for caching challenges, nonces, and real-time state.
- **Security**: 
  - **WebAuthn (FIDO2)**: For hardware-backed biometric and device verification.
  - **JWT (Enhanced)**: Structured tokens with metadata for session tracking.
- **Monitoring & Observability**:
  - **Prometheus**: Real-time metrics collection.
  - **OpenTelemetry**: Distributed tracing for performance analysis.
  - **Structured Logging**: JSON-formatted logs for ELK/Loki integration.
- **Background Tasks**: Celery/Redis for asynchronous ML processing and email notifications.

### Frontend
- **Framework**: [React](https://reactjs.org/) with [Vite](https://vitejs.dev/) for fast development and optimized builds.
- **Language**: TypeScript (Strict mode).
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) for utility-first responsive design.
- **State Management**: [Zustand](https://github.com/pmndrs/zustand) for lightweight, high-performance global state.
- **Animations**: [Framer Motion](https://www.framer.com/motion/) for premium, fluid UI transitions.
- **Icons**: [Lucide React](https://lucide.dev/).
- **Charts**: [Recharts](https://recharts.org/) for faculty analytics.

### Infrastructure
- **Docker & Docker Compose**: Containerization for consistent development and deployment environments.
- **MinIO**: S3-compatible storage for lecture recordings and curriculum assets.
- **Nginx**: Reverse proxy and static file server.

---

## 3. System Architecture

### High-Level Components
1.  **API Gateway (FastAPI)**: Routes requests, handles authentication, and enforces RBAC.
2.  **Zero-Trust Engine**: Validates attendance across 6 spatial and cryptographic gates.
3.  **Curriculum Engine**: Manages the dependency graph of course materials and unlocks content based on attendance events.
4.  **Analytics Service (ML)**: Processes audio/attendance data to detect collusion and predict student risk.
5.  **Real-Time Bridge (WebSockets)**: Provides live updates to the Faculty Dashboard.

---

## 4. Backend: Functional Breakdown

### `app/main.py`
The entry point of the application.
- **Lifespan Management**: Initializes MongoDB connections, JWT security, and Prometheus metrics.
- **Middleware**: 
  - `TracingMiddleware`: Captures spans for distributed tracing.
  - `MetricsMiddleware`: Records request latency and error rates.
  - `CORSMiddleware`: Manages cross-origin security.
- **Router Integration**: Aggregates all modular routers under `/api`.

### `app/routers/attendance.py`
Implements the core business logic for student check-ins.
- **`list_active_sessions`**: Fetches all ongoing lectures with metadata (instructor, occupancy).
- **`checkin_attendance`**: The most critical function. It processes 6 "gates":
  - **Gate 1 (Biometric/Device)**: Verifies WebAuthn signatures via `verify_authentication_response`.
  - **Gate 2 (Spatial)**: Checks geofence boundaries via `calculate_haversine` or `ray_casting_polygon`.
  - **Gate 3 (Kinematic)**: Validates velocity via `verify_kinematic_velocity` to detect GPS spoofing.
  - **Gate 4 (Nonce)**: Ensures request freshness to prevent replay attacks.
  - **Gate 5 (Multimodal)**: Cross-references network and environmental signals.
- **`get_audit_queue`**: Retrieves attendance logs flagged for manual review (`moderate` status).
- **`process_audit`**: Allows faculty to `approve` or `reject` flagged logs with a justification.

### `app/services/curriculum_engine.py`
Manages the "Knowledge Graph" traversal and student progress.
- **`process_curriculum_unlocks`**: 
  - Triggered after successful attendance check-in.
  - Traverses the graph to find nodes (materials) tied to the `session_id`.
  - Checks if all `prerequisites` are present in `student_progress`.
  - Updates the student's unlocked set and logs the event.

### `app/security/auth_enhanced.py` & `app/security/rbac.py`
- **`get_jwt_security`**: Validates tokens and checks against a blacklist (token rotation).
- **`RBACEnforcer`**: Decorator/Dependency that restricts access based on `RoleEnum` (Admin, Faculty, Student).
- **`generate_webauthn_challenge`**: Creates a cryptographically secure challenge for biometric binding.

### `app/ml/` (Machine Learning)
- **`collusion_detector.py`**: Analyzes check-in patterns to identify "buddy punching" (one student checking in for multiple friends).
- **`local_whisper.py`**: Transcribes lecture audio using OpenAI's Whisper model.
- **`risk_model.py`**: Predictive model that flags students at risk of failing based on attendance trends.

---

## 5. Frontend: Feature Modules

### `src/features/attendance/`
- **`MarkAttendanceFlow.tsx`**: A multi-step guided UI that handles Geolocation API calls and WebAuthn handshake.
- **`VerificationStatus.tsx`**: Provides real-time feedback to the student about which "gates" they passed or failed.

### `src/features/faculty/`
- **`FacultyOverview.tsx`**: High-level metrics (Class occupancy, average engagement).
- **`PredictiveAnalyticsPage.tsx`**: Visualizes ML-derived risks and collusion alerts.
- **`VerificationQueuePage.tsx`**: A triage interface for faculty to review flagged attendance logs.

### `src/features/curriculum/`
- **`CurriculumMap.tsx`**: An interactive visualization of the knowledge graph, showing locked and unlocked nodes.

---

## 6. Database Schema (MongoDB)

| Collection | Description | Key Fields |
| :--- | :--- | :--- |
| `users` | User profiles and RBAC | `email`, `role`, `webauthn_credentials` |
| `attendance_logs` | Verified/Flagged attendance | `user_id`, `session_id`, `gates_passed`, `status` |
| `geofences` | Campus/Classroom boundaries | `name`, `type`, `boundary` (GeoJSON), `radius` |
| `curriculum_nodes` | Course materials | `title`, `type`, `url`, `prerequisites` |
| `student_progress` | Track unlocked items | `user_id`, `unlocked_node_ids` |

---

## 7. Key Workflows

### The Zero-Trust Attendance Flow
1.  **Request**: Student triggers check-in via mobile device.
2.  **Geolocation**: App captures latitude/longitude.
3.  **Challenge**: Backend issues a WebAuthn challenge.
4.  **Hardware Verification**: Student uses Biometrics (Fingerprint/FaceID) to sign the challenge.
5.  **Multi-Gate Check**: Backend validates Geofence, Velocity, Signature, and Nonce.
6.  **Outcome**: If all 6 pass, attendance is marked `verified`, curriculum is unlocked, and faculty see a real-time update.

### Curriculum Synchronization
1.  Faculty starts a lecture session.
2.  System maps the `session_id` to a node in the Knowledge Graph.
3.  Upon student check-in, the system "unlocks" the node and child nodes for which prerequisites are now satisfied.

---

## 8. Deployment & Development

### Setup
1.  **Clone**: `git clone <repo_url>`
2.  **Backend**: 
    - `cd backend`
    - `python -m venv venv && source venv/bin/activate`
    - `pip install -r requirements.txt`
    - `uvicorn app.main:app --reload`
3.  **Frontend**:
    - `cd frontend`
    - `npm install`
    - `npm run dev`
4.  **Docker (Recommended)**:
    - `docker-compose up --build`

### Documentation Files
- `BACKEND_ARCHITECTURE.md`: Deep dive into backend internals.
- `ARCHITECTURE.md` (Frontend): Detailed frontend state and component design.
- `ANALYTICS_INTEGRATION_GUIDE.md`: How the ML services communicate with the core API.

---

**ScholarLab** is designed to be extensible, secure, and user-centric, bridging the gap between physical attendance and digital learning progress.
