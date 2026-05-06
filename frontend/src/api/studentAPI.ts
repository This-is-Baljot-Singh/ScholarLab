/**
 * API service layer for student attendance and curriculum endpoints
 */

import { apiClient } from '@/api/client';
import type {
  AttendanceSession,
  SessionNonce,
  AttendanceCheckInRequest,
  AttendanceCheckInResponse,
  UnlockedResource,
} from '@/types/dashboard';

/**
 * Attendance API endpoints
 */
export const attendanceAPI = {
  /**
   * Fetch active sessions for today
   * GET /api/attendance/sessions
   */
  getSessions: async (): Promise<AttendanceSession[]> => {
    try {
      const response = await apiClient.get('/attendance/sessions');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch attendance sessions:', error);
      throw error;
    }
  },

  /**
   * Request a nonce for attendance check-in
   * POST /api/attendance/sessions/{sessionId}/nonce
   */
  requestNonce: async (sessionId: string): Promise<SessionNonce> => {
    try {
      const response = await apiClient.post(
        `/attendance/sessions/${sessionId}/nonce`,
        {}
      );
      return response.data;
    } catch (error) {
      console.error('Failed to request nonce:', error);
      throw error;
    }
  },

  /**
   * Submit attendance check-in
   * POST /api/attendance/checkin
   */
  submitCheckIn: async (
    checkInData: AttendanceCheckInRequest
  ): Promise<AttendanceCheckInResponse> => {
    try {
      const response = await apiClient.post('/attendance/checkin', checkInData);
      return response.data;
    } catch (error) {
      console.error('Failed to submit check-in:', error);
      throw error;
    }
  },

  /**
   * Get attendance statistics for student
   * GET /api/attendance/stats
   */
  getAttendanceStats: async (): Promise<{
    totalSessions: number;
    attendedSessions: number;
    attendanceRate: number;
  }> => {
    try {
      const response = await apiClient.get('/attendance/stats');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch attendance stats:', error);
      throw error;
    }
  },
};

/**
 * Curriculum API endpoints
 */
export const curriculumAPI = {
  /**
   * Fetch unlocked curriculum resources for a session
   * GET /api/curriculum/resources/{sessionId}
   */
  getSessionResources: async (
    sessionId: string
  ): Promise<UnlockedResource[]> => {
    try {
      const response = await apiClient.get(
        `/curriculum/resources/${sessionId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch curriculum resources:', error);
      throw error;
    }
  },

  /**
   * Fetch all unlocked curriculum items for student
   * GET /api/curriculum/unlocked
   */
  getUnlockedItems: async (): Promise<UnlockedResource[]> => {
    try {
      const response = await apiClient.get('/curriculum/unlocked');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch unlocked curriculum:', error);
      throw error;
    }
  },
};

/**
 * Analytics API endpoints
 */
export const analyticsAPI = {
  /**
   * Get student performance metrics
   * GET /api/analytics/performance
   */
  getPerformanceMetrics: async (): Promise<{
    attendanceRate: number;
    curriculumEngagement: number;
    riskScore: number;
  }> => {
    try {
      const response = await apiClient.get('/analytics/performance');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
      throw error;
    }
  },
};
