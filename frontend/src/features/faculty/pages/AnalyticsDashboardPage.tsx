import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { PredictiveAnalyticsDashboard } from '../components';
import type { AttendanceTrendData, StudentRiskData, StudentAnalytics } from '@/types/faculty';

interface AnalyticsDashboardPageProps {
  onBack: () => void;
}

export const AnalyticsDashboardPage: React.FC<AnalyticsDashboardPageProps> = ({ onBack }) => {
  const [attendanceTrends] = useState<AttendanceTrendData[]>([
    { date: '2026-04-13', totalSessions: 4, avgAttendance: 28, attendanceRate: 87.5 },
    { date: '2026-04-14', totalSessions: 5, avgAttendance: 31, attendanceRate: 93.2 },
    { date: '2026-04-15', totalSessions: 4, avgAttendance: 26, attendanceRate: 81.2 },
    { date: '2026-04-16', totalSessions: 6, avgAttendance: 32, attendanceRate: 95.1 },
    { date: '2026-04-17', totalSessions: 5, avgAttendance: 25, attendanceRate: 78.9 },
    { date: '2026-04-18', totalSessions: 4, avgAttendance: 29, attendanceRate: 90.6 },
    { date: '2026-04-19', totalSessions: 5, avgAttendance: 27, attendanceRate: 84.4 },
  ]);

  const [atRiskStudents] = useState<StudentRiskData[]>([
    {
      studentId: 'student-1',
      name: 'John Martinez',
      email: 'jmartinez@example.edu',
      riskScore: 85,
      riskLevel: 'high',
      lastSeen: '2026-04-17T10:30:00Z',
      absenceCount: 6,
      avgAttendanceRate: 42,
      reasons: ['High absence rate', 'Declining engagement', 'Missing assignments'],
    },
    {
      studentId: 'student-2',
      name: 'Sarah Johnson',
      email: 'sjohnson@example.edu',
      riskScore: 72,
      riskLevel: 'high',
      lastSeen: '2026-04-16T14:15:00Z',
      absenceCount: 4,
      avgAttendanceRate: 55,
      reasons: ['Inconsistent participation', 'Recent decline in performance'],
    },
    {
      studentId: 'student-3',
      name: 'Michael Chen',
      email: 'mchen@example.edu',
      riskScore: 58,
      riskLevel: 'medium',
      lastSeen: '2026-04-19T11:00:00Z',
      absenceCount: 3,
      avgAttendanceRate: 68,
      reasons: ['Below average engagement', 'Occasional absences'],
    },
    {
      studentId: 'student-4',
      name: 'Emma Wilson',
      email: 'ewilson@example.edu',
      riskScore: 44,
      riskLevel: 'medium',
      lastSeen: '2026-04-18T09:45:00Z',
      absenceCount: 2,
      avgAttendanceRate: 75,
      reasons: ['Minor engagement concerns'],
    },
    {
      studentId: 'student-5',
      name: 'David Brown',
      email: 'dbrown@example.edu',
      riskScore: 92,
      riskLevel: 'high',
      lastSeen: '2026-04-15T13:20:00Z',
      absenceCount: 7,
      avgAttendanceRate: 38,
      reasons: ['Severe absence pattern', 'Lost connection with coursework', 'Critical intervention needed'],
    },
    {
      studentId: 'student-6',
      name: 'Lisa Anderson',
      email: 'landerson@example.edu',
      riskScore: 61,
      riskLevel: 'medium',
      lastSeen: '2026-04-19T15:30:00Z',
      absenceCount: 2,
      avgAttendanceRate: 72,
      reasons: ['Potential early warning signs'],
    },
    {
      studentId: 'student-7',
      name: 'Robert Taylor',
      email: 'rtaylor@example.edu',
      riskScore: 79,
      riskLevel: 'high',
      lastSeen: '2026-04-14T10:15:00Z',
      absenceCount: 5,
      avgAttendanceRate: 50,
      reasons: ['High absenteeism', 'Disengagement trend'],
    },
    {
      studentId: 'student-8',
      name: 'Jessica Lee',
      email: 'jlee@example.edu',
      riskScore: 52,
      riskLevel: 'medium',
      lastSeen: '2026-04-19T12:45:00Z',
      absenceCount: 1,
      avgAttendanceRate: 80,
      reasons: ['Borderline engagement'],
    },
  ]);

  const [studentAnalytics] = useState<Record<string, StudentAnalytics>>({
    'student-1': {
      studentId: 'student-1',
      riskScore: 85,
      predictions: [
        { feature: 'Total Absences', contribution: 0.28, baseValue: 50 },
        { feature: 'Declining Engagement', contribution: 0.18, baseValue: 50 },
        { feature: 'Assignment Completion', contribution: -0.15, baseValue: 50 },
        { feature: 'Recent Session Count', contribution: -0.08, baseValue: 50 },
        { feature: 'Course Interaction Time', contribution: 0.12, baseValue: 50 },
      ],
    },
    'student-2': {
      studentId: 'student-2',
      riskScore: 72,
      predictions: [
        { feature: 'Inconsistent Participation', contribution: 0.22, baseValue: 50 },
        { feature: 'Performance Decline', contribution: 0.15, baseValue: 50 },
        { feature: 'Quiz Scores', contribution: -0.10, baseValue: 50 },
        { feature: 'Forum Activity', contribution: -0.05, baseValue: 50 },
      ],
    },
    'student-3': {
      studentId: 'student-3',
      riskScore: 58,
      predictions: [
        { feature: 'Below Average Engagement', contribution: 0.12, baseValue: 50 },
        { feature: 'Occasional Absences', contribution: 0.08, baseValue: 50 },
        { feature: 'Lab Submission Time', contribution: -0.05, baseValue: 50 },
      ],
    },
    'student-5': {
      studentId: 'student-5',
      riskScore: 92,
      predictions: [
        { feature: 'Severe Absence Pattern', contribution: 0.35, baseValue: 50 },
        { feature: 'Lost Connection', contribution: 0.25, baseValue: 50 },
        { feature: 'Zero Assignment Submission', contribution: 0.20, baseValue: 50 },
        { feature: 'No Course Interaction', contribution: 0.12, baseValue: 50 },
      ],
    },
  });

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <Button onClick={onBack} variant="ghost" size="sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Predictive Analytics Dashboard</h1>
          <p className="text-slate-600 text-sm mt-1">
            ML-powered student risk assessment with SHAP model explanations
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <PredictiveAnalyticsDashboard
          attendanceTrends={attendanceTrends}
          atRiskStudents={atRiskStudents}
          studentAnalytics={studentAnalytics}
        />
      </div>
    </div>
  );
};
