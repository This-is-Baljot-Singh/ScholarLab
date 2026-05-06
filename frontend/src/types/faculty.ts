// Geofence Types
export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface CircularGeofence {
  type: 'circle';
  center: GeoPoint;
  radiusMeters: number;
}

export interface PolygonGeofence {
  type: 'polygon';
  coordinates: GeoPoint[];
}

export type Geofence = CircularGeofence | PolygonGeofence;

export interface BaseGeofence {
  id: string;
  name: string;
  buildingCode?: string;
  createdAt: string;
  updatedAt: string;
}

export type GeofenceWithMetadata = (CircularGeofence & BaseGeofence) | (PolygonGeofence & BaseGeofence);

// Curriculum Graph Types
export interface CurriculumNode {
  id: string;
  title: string;
  description?: string;
  resources: CurriculumResource[];
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
  estimatedHours?: number;
  prerequisites?: string[]; // Array of node IDs
}

export interface CurriculumResource {
  id: string;
  title: string;
  type: 'pdf' | 'video' | 'link' | 'quiz' | 'assignment';
  uri: string;
  createdAt: string;
}

export interface CurriculumGraph {
  id: string;
  title: string;
  description?: string;
  nodes: CurriculumNode[];
  edges: Array<{
    source: string; // node ID
    target: string; // node ID
  }>;
  createdAt: string;
  updatedAt: string;
}

// Session Types
export interface LiveSession {
  id: string;
  lectureId: string;
  currentCurriculumNodeId: string;
  geofenceId: string;
  facultyId: string;
  startTime: string;
  endTime?: string;
  status: 'active' | 'completed';
  attendanceCount: number;
}

export interface SessionInitPayload {
  lectureId: string;
  curriculumNodeId: string;
  geofenceId: string;
}

// Analytics Types
export interface AttendanceTrendData {
  date: string;
  totalSessions: number;
  avgAttendance: number;
  attendanceRate: number; // percentage
}

export interface StudentRiskData {
  studentId: string;
  name: string;
  email: string;
  riskScore: number; // 0-100
  riskLevel: 'low' | 'medium' | 'high';
  lastSeen: string;
  absenceCount: number;
  avgAttendanceRate: number;
  reasons: string[]; // SHAP feature importance labels
}

export interface SHAPExplanation {
  feature: string;
  contribution: number; // SHAP value (can be positive or negative)
  baseValue: number;
}

export interface StudentAnalytics {
  studentId: string;
  riskScore: number;
  predictions: SHAPExplanation[];
}

export interface FacultyDashboard {
  geofences: GeofenceWithMetadata[];
  curriculumGraphs: CurriculumGraph[];
  activeSessions: LiveSession[];
  analyticsData: {
    attendanceTrends: AttendanceTrendData[];
    atRiskStudents: StudentRiskData[];
  };
}

// ---------------------------------------------------------------------------
// Session-Close Workflow Types
// (mirror backend/app/routers/curriculum.py Pydantic schemas)
// ---------------------------------------------------------------------------

/** Payload sent to POST /api/curriculum/session/close */
export interface SessionClosePayload {
  /** The live session being closed */
  session_id: string;
  /** IDs of curriculum nodes covered during this session (faculty selection) */
  node_ids: string[];
  /** Optional: parent curriculum graph ID, for context */
  graph_id?: string;
}

/** Response returned immediately (before background task completes) */
export interface SessionCloseResponse {
  session_id: string;
  /** Number of curriculum nodes atomically marked as completed */
  nodes_completed: number;
  /** Number of students whose risk features will be updated asynchronously */
  absent_students: number;
  /** UUID for tracing the async risk-feature recomputation task */
  background_task_id: string;
}

// ---------------------------------------------------------------------------
// Anti-Spoofing Audit Trail Types
// ---------------------------------------------------------------------------

export interface AuditQueueRecord {
  id: string;
  studentId: string;
  studentName: string;
  sessionId: string;
  timestamp: string;
  metadata: {
    flag_reason?: string;
    [key: string]: any;
  };
}

export interface AuditActionPayload {
  approve: boolean;
  justification: string;
}

// ---------------------------------------------------------------------------
// Curriculum Verification Types
// ---------------------------------------------------------------------------

export type VerificationStatus = 'pending' | 'approved' | 'rejected' | 'corrected';

export interface VerificationTask {
  task_id: string;
  session_id: string;
  course_id: string;
  topic: string;
  topic_confidence: number;
  original_node_id: string;
  original_node_title: string;
  similarity_score: number;
  status: VerificationStatus;
  faculty_id?: string;
  verified_at?: string;
  notes?: string;
  corrected_node_id?: string;
  corrected_node_title?: string;
}

export interface VerifyActionPayload {
  action: 'approve' | 'reject' | 'correct';
  notes?: string;
  corrected_node_id?: string;
  corrected_node_title?: string;
}

export interface CurriculumAudioResponse {
  message: string;
  task_id: string;
  object_key: string;
  privacy_mode: string;
}

// ---------------------------------------------------------------------------
// Active Classroom Types
// ---------------------------------------------------------------------------

export interface ActiveClassroom {
  sessionId: string;
  courseId: string;
  courseTitle: string;
  instructorName: string;
  startTime: string;
  location: string;
  totalEnrolled: number;
  successfulCheckIns: number;
  flaggedForReview: number;
}

export interface ClassroomCheckInStats {
  sessionId: string;
  totalStudents: number;
  checkedIn: number;
  flagged: number;
  percentage: number;
}

// ---------------------------------------------------------------------------
// Student Management Types
// ---------------------------------------------------------------------------

export interface EnrolledStudent {
  id: string;
  name: string;
  email: string;
  studentId: string;
  enrolledCourses: string[];
  attendanceRate: number; // 0-100%
  riskLevel: 'green' | 'yellow' | 'red';
  riskScore: number; // 0-100
  lastAttendance?: string;
  recentFlags?: number;
  avgEngagement: number; // 0-100%
}

export interface StudentEnrollmentResponse {
  students: EnrolledStudent[];
  totalEnrolled: number;
  courseId: string;
}

export interface StudentCheckInStatus {
  studentId: string;
  name: string;
  email: string;
  hasCheckedIn: boolean;
  checkInTime?: string;
  flagged: boolean;
  flagReason?: string;
  riskScore: number;
}
