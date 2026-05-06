/**
 * API service layer for faculty endpoints
 */

import { apiClient } from '@/lib/api';
import type {
  ActiveClassroom,
  ClassroomCheckInStats,
  EnrolledStudent,
  StudentEnrollmentResponse,
} from '@/types/faculty';

/**
 * Classroom API endpoints
 */
export const classroomAPI = {
  /**
   * Get current active classroom/session details
   * GET /api/classroom/active
   */
  getActiveClassroom: async (): Promise<ActiveClassroom> => {
    try {
      const response = await apiClient.get('/classroom/active');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch active classroom:', error);
      throw error;
    }
  },

  /**
   * Get check-in statistics for active session
   * GET /api/classroom/sessions/{sessionId}/checkin-stats
   */
  getCheckInStats: async (sessionId: string): Promise<ClassroomCheckInStats> => {
    try {
      const response = await apiClient.get(`/classroom/sessions/${sessionId}/checkin-stats`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch check-in stats:', error);
      throw error;
    }
  },

  /**
   * Get real-time check-in status for all students in session
   * GET /api/classroom/sessions/{sessionId}/checkin-status
   */
  getCheckInStatus: async (sessionId: string) => {
    try {
      const response = await apiClient.get(`/classroom/sessions/${sessionId}/checkin-status`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch check-in status:', error);
      throw error;
    }
  },
};

/**
 * Student Management API endpoints
 */
export const studentManagementAPI = {
  /**
   * Get enrolled students for a course
   * GET /api/courses/{courseId}/students
   */
  getEnrolledStudents: async (courseId: string): Promise<StudentEnrollmentResponse> => {
    try {
      const response = await apiClient.get(`/courses/${courseId}/students`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch enrolled students:', error);
      throw error;
    }
  },

  /**
   * Get attendance percentage for student in course
   * GET /api/courses/{courseId}/students/{studentId}/attendance
   */
  getStudentAttendance: async (
    courseId: string,
    studentId: string
  ): Promise<{ attendanceRate: number; sessionsAttended: number; totalSessions: number }> => {
    try {
      const response = await apiClient.get(
        `/courses/${courseId}/students/${studentId}/attendance`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch student attendance:', error);
      throw error;
    }
  },

  /**
   * Get student risk profile
   * GET /api/students/{studentId}/risk
   */
  getStudentRisk: async (studentId: string) => {
    try {
      const response = await apiClient.get(`/students/${studentId}/risk`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch student risk:', error);
      throw error;
    }
  },

  /**
   * Get all students with risk scores and attendance (for management table)
   * GET /api/faculty/class/students-summary?course_id={courseId}
   */
  getStudentsSummary: async (courseId: string): Promise<EnrolledStudent[]> => {
    try {
      const response = await apiClient.get(
        `/faculty/class/students-summary?course_id=${courseId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch students summary:', error);
      throw error;
    }
  },
};

/**
 * Session Management API endpoints
 */
export const sessionManagementAPI = {
  /**
   * Get current teaching session
   * GET /api/sessions/current
   */
  getCurrentSession: async () => {
    try {
      const response = await apiClient.get('/sessions/current');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch current session:', error);
      throw error;
    }
  },

  /**
   * Get session details by ID
   * GET /api/sessions/{sessionId}
   */
  getSession: async (sessionId: string) => {
    try {
      const response = await apiClient.get(`/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch session:', error);
      throw error;
    }
  },
};
