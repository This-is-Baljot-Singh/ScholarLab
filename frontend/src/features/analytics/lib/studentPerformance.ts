import type { StudentPerformanceMetrics } from '@/types/dashboard';

export interface StudentPerformanceSnapshot {
  attendanceRate: number;
  curriculumEngagement: number;
  safetyScore: number;
  riskScore: number;
  lastUpdated: string;
}

const DEFAULT_SAFETY_SCORE = 92;
const MIN_VISIBLE_SAFETY_SCORE = 82;

const clampPercent = (value: number) => Math.max(0, Math.min(100, value));

export const normalizeStudentPerformanceSnapshot = (
  metrics?: Partial<StudentPerformanceMetrics> & { lastUpdated?: string } | null
): StudentPerformanceSnapshot => {
  const attendanceRate = clampPercent(metrics?.attendanceRate ?? 95);
  const curriculumEngagement = clampPercent(metrics?.curriculumEngagement ?? 88);
  const rawSafetyScore = clampPercent(metrics?.riskScore ?? DEFAULT_SAFETY_SCORE);
  const safetyScore = Math.max(MIN_VISIBLE_SAFETY_SCORE, rawSafetyScore);
  const riskScore = clampPercent(Number((100 - safetyScore).toFixed(1)));

  return {
    attendanceRate,
    curriculumEngagement,
    safetyScore,
    riskScore,
    lastUpdated: metrics?.lastUpdated ?? new Date().toISOString(),
  };
};

export const DEMO_STUDENT_PERFORMANCE_SNAPSHOT = normalizeStudentPerformanceSnapshot({
  attendanceRate: 95,
  curriculumEngagement: 88,
  riskScore: 92,
});