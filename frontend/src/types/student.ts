export interface Lecture {
  id: string;
  title: string;
  description: string;
  instructor: string;
  startTime: string;
  endTime: string;
  location: string;
  classCode: string;
}

export interface ActiveSession {
  lecture: Lecture;
  isOngoing: boolean;
  attendanceMarked: boolean;
  markedTime?: string;
}

export interface AttendanceVerification {
  lectureId: string;
  latitude: number;
  longitude: number;
  accuracy: number;
  credentialId: string;
  clientDataJSON: string;
  signature: string;
  authenticatorData: string;
  timestamp: string;
}

export interface AttendanceRecord {
  id: string;
  lectureId: string;
  lectureTitle: string;
  date: string;
  markedTime: string;
  status: 'present' | 'absent' | 'late';
  latitude?: number;
  longitude?: number;
}

export interface CurriculumItem {
  id: string;
  lectureId: string;
  title: string;
  type: 'pdf' | 'quiz' | 'video' | 'assignment';
  isUnlocked: boolean;
  unlockedAt?: string;
  url?: string;
  metadata?: {
    duration?: number;
    pages?: number;
    points?: number;
  };
}

export interface StudentDashboard {
  activeSession?: ActiveSession;
  upcomingLectures: Lecture[];
  recentAttendance: AttendanceRecord[];
  unlockedCurriculum: CurriculumItem[];
}
