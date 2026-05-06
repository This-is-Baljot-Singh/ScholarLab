/**
 * Dashboard types for Student Profile and Analytics
 */

export interface AttendanceSession {
  id: string;
  lectureId: string;
  title: string;
  instructor: string;
  startTime: string;
  endTime: string;
  location: string;
  classCode: string;
  status: 'upcoming' | 'ongoing' | 'completed';
  geofenceLatitude: number;
  geofenceLongitude: number;
  geofenceRadius: number;
}

export interface SessionNonce {
  nonce: string;
  expiresAt: string;
  sessionId: string;
}

export interface AttendanceCheckInRequest {
  sessionId: string;
  nonce: string;
  latitude: number;
  longitude: number;
  accuracy: number;
  credentialId: string;
  clientDataJSON: string;
  authenticatorData: string;
  signature: string;
}

export interface AttendanceCheckInResponse {
  checkInId: string;
  sessionId: string;
  timestamp: string;
  status: 'success' | 'failed';
  gates: {
    geofence: boolean;
    cryptographic: boolean;
    multimodal: boolean;
    nonce: boolean;
    biometric: boolean;
    device: boolean;
  };
  message: string;
}

export interface UnlockedResource {
  id: string;
  sessionId: string;
  title: string;
  type: 'pdf' | 'slides' | 'video' | 'quiz' | 'assignment';
  url: string;
  unlockedAt: string;
  description?: string;
  metadata?: {
    duration?: number;
    pages?: number;
    points?: number;
  };
}

export interface StudentPerformanceMetrics {
  attendanceRate: number; // 0-100
  curriculumEngagement: number; // 0-100
  riskScore: number; // 0-100 (inverted: 100 = safe, 0 = risky)
  lastUpdated: string;
}

export interface LocationCheckConfig {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export interface WebAuthnCheckConfig {
  challenge: string;
  timeout: number;
  userVerification: 'required' | 'preferred' | 'discouraged';
}

export interface AttendanceFlowState {
  step: 'idle' | 'location' | 'biometric' | 'success' | 'error';
  sessionId?: string;
  nonce?: string;
  location?: LocationCheckConfig;
  webauthnConfig?: WebAuthnCheckConfig;
  error?: string;
  checkInResponse?: AttendanceCheckInResponse;
}
