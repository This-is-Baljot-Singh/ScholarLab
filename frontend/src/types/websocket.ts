/**
 * ScholarLab — Faculty WebSocket Event Types
 * ============================================
 * These interfaces MUST stay in sync with the Pydantic schemas defined in
 * `backend/app/services/websocket.py`.
 *
 * Three event types flow over ws://localhost:8000/ws/faculty/{session_id}:
 *   1. attendance_verified     — student cleared the full verification pipeline
 *   2. spoofing_attempt_detected — biometric / spatial check failed
 *   3. risk_score_updated      — ML model re-evaluated an individual student
 */

// ---------------------------------------------------------------------------
// Individual event payloads
// ---------------------------------------------------------------------------

export interface AttendanceVerifiedEvent {
  type: 'attendance_verified';
  /** MongoDB ObjectId string of the student */
  student_id: string;
  student_name: string;
  session_id: string;
  /** UTC ISO 8601 timestamp */
  timestamp: string;
  /** Running total of verified attendances for this session */
  attendance_count: number;
}

export interface SpoofingAttemptEvent {
  type: 'spoofing_attempt_detected';
  session_id: string;
  /** UTC ISO 8601 timestamp */
  attempted_at: string;
  /** Human-readable reason for the rejection */
  reason: string;
}

export interface RiskScoreUpdatedEvent {
  type: 'risk_score_updated';
  /** MongoDB ObjectId string of the student */
  student_id: string;
  /** Raw XGBoost probability — 0.0 to 1.0 */
  new_risk_score: number;
  risk_label: 'Safe' | 'At Risk' | 'Critical';
}

// ---------------------------------------------------------------------------
// Discriminated union — use `event.type` to narrow to the concrete interface
// ---------------------------------------------------------------------------

export type FacultyWSEvent =
  | AttendanceVerifiedEvent
  | SpoofingAttemptEvent
  | RiskScoreUpdatedEvent;

// ---------------------------------------------------------------------------
// WebSocket connection state
// ---------------------------------------------------------------------------

export type WSConnectionState =
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'failed'
  | 'closed';
