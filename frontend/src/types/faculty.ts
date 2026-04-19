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
