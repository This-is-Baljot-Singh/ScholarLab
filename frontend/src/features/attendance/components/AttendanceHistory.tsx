import React from 'react';
import { CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { AttendanceRecordSkeleton } from '@/shared/ui/SkeletonLoader';
import type { AttendanceRecord } from '@/types/student';

interface AttendanceHistoryProps {
  records: AttendanceRecord[];
  isLoading?: boolean;
}

interface AttendanceSummary {
  total: number;
  present: number;
  absent: number;
  late: number;
  attendanceRate: number;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'present':
      return <CheckCircle className="h-5 w-5 text-green-600" />;
    case 'late':
      return <Clock className="h-5 w-5 text-amber-600" />;
    case 'absent':
      return <AlertCircle className="h-5 w-5 text-red-600" />;
    default:
      return null;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'present':
      return 'bg-green-50 border-green-200';
    case 'late':
      return 'bg-amber-50 border-amber-200';
    case 'absent':
      return 'bg-red-50 border-red-200';
    default:
      return 'bg-slate-50 border-slate-200';
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'present':
      return 'Present';
    case 'late':
      return 'Late';
    case 'absent':
      return 'Absent';
    default:
      return 'Unknown';
  }
};

const calculateSummary = (records: AttendanceRecord[]): AttendanceSummary => {
  const summary = {
    total: records.length,
    present: records.filter((r) => r.status === 'present').length,
    absent: records.filter((r) => r.status === 'absent').length,
    late: records.filter((r) => r.status === 'late').length,
    attendanceRate: 0,
  };

  if (summary.total > 0) {
    summary.attendanceRate = Math.round(
      ((summary.present + summary.late * 0.5) / summary.total) * 100
    );
  }

  return summary;
};

export const AttendanceHistory: React.FC<AttendanceHistoryProps> = ({
  records,
  isLoading = false,
}) => {
  const summary = calculateSummary(records);

  if (isLoading) {
    return <AttendanceRecordSkeleton count={5} />;
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* Attendance Rate */}
        <div className="rounded-xl bg-gradient-to-br from-green-50 to-green-100 p-4">
          <p className="text-xs text-green-700">Attendance Rate</p>
          <p className="mt-1 text-2xl font-bold text-green-700">{summary.attendanceRate}%</p>
        </div>

        {/* Total Classes */}
        <div className="rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 p-4">
          <p className="text-xs text-blue-700">Total Classes</p>
          <p className="mt-1 text-2xl font-bold text-blue-700">{summary.total}</p>
        </div>

        {/* Present */}
        <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100 p-4">
          <p className="text-xs text-emerald-700">Present</p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">{summary.present}</p>
        </div>

        {/* Late/Absent */}
        <div className="rounded-xl bg-gradient-to-br from-orange-50 to-orange-100 p-4">
          <p className="text-xs text-orange-700">Late/Absent</p>
          <p className="mt-1 text-2xl font-bold text-orange-700">
            {summary.late + summary.absent}
          </p>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-2">
        <h3 className="font-semibold text-slate-900">Recent Attendance</h3>

        {records.length === 0 ? (
          <div className="rounded-lg bg-slate-50 p-6 text-center">
            <p className="text-sm text-slate-600">No attendance records yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {records.map((record, index) => (
              <div
                key={record.id}
                className={`relative border border-l-4 rounded-lg p-4 transition-all duration-200 ${getStatusColor(record.status)}`}
              >
                {/* Timeline line */}
                {index < records.length - 1 && (
                  <div className="absolute -bottom-3 left-5 h-3 w-0.5 bg-slate-300" />
                )}

                <div className="flex items-start gap-4">
                  {/* Status Icon */}
                  <div className="flex-shrink-0 pt-1">
                    {getStatusIcon(record.status)}
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold text-slate-900">
                        {record.lectureTitle}
                      </p>
                      <span className="inline-block rounded-full bg-slate-200 px-2 py-1 text-xs font-medium text-slate-700">
                        {getStatusLabel(record.status)}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-600">
                      <span>📅 {new Date(record.date).toLocaleDateString()}</span>
                      <span>⏰ {record.markedTime}</span>

                      {record.latitude && record.longitude && (
                        <span>
                          📍 Verified at location
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
