/**
 * Zustand store for student dashboard and attendance flow
 */

import { create } from 'zustand';
import type { AttendanceFlowState } from '@/types/dashboard';

interface StudentDashboardStore {
  // Attendance flow state
  attendanceFlow: AttendanceFlowState;
  setAttendanceFlow: (state: AttendanceFlowState) => void;
  updateAttendanceFlow: (partial: Partial<AttendanceFlowState>) => void;
  resetAttendanceFlow: () => void;

  // Session state
  selectedSessionId: string | null;
  setSelectedSessionId: (sessionId: string | null) => void;

  // UI state
  isMarkingAttendance: boolean;
  setIsMarkingAttendance: (isMarking: boolean) => void;
  showAttendanceModal: boolean;
  setShowAttendanceModal: (show: boolean) => void;

  // Cache invalidation triggers
  shouldRefreshResources: boolean;
  setShouldRefreshResources: (should: boolean) => void;
}

const initialAttendanceFlow: AttendanceFlowState = {
  step: 'idle',
};

export const useStudentDashboardStore = create<StudentDashboardStore>(
  (set) => ({
    // Attendance flow
    attendanceFlow: initialAttendanceFlow,
    setAttendanceFlow: (state) => set({ attendanceFlow: state }),
    updateAttendanceFlow: (partial) =>
      set((prev) => ({
        attendanceFlow: { ...prev.attendanceFlow, ...partial },
      })),
    resetAttendanceFlow: () =>
      set({ attendanceFlow: initialAttendanceFlow, isMarkingAttendance: false }),

    // Session
    selectedSessionId: null,
    setSelectedSessionId: (sessionId) => set({ selectedSessionId: sessionId }),

    // UI state
    isMarkingAttendance: false,
    setIsMarkingAttendance: (isMarking) =>
      set({ isMarkingAttendance: isMarking }),
    showAttendanceModal: false,
    setShowAttendanceModal: (show) => set({ showAttendanceModal: show }),

    // Cache
    shouldRefreshResources: false,
    setShouldRefreshResources: (should) =>
      set({ shouldRefreshResources: should }),
  })
);
