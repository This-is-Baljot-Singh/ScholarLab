import React, { useState } from 'react';
import { AlertTriangle, ChevronRight, Loader2, AlertCircle, ServerCrash } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { StudentRiskModal } from './StudentRiskModal';

interface AtRiskStudent {
  id: string;
  name: string;
  email: string;
  riskScore: number;
  riskLabel: 'Safe' | 'At Risk' | 'Critical';
  lastSeen?: string;
}

export const AtRiskStudentsList: React.FC = () => {
  const [selectedStudent, setSelectedStudent] = useState<string | undefined>(undefined);
  const [selectedStudentName, setSelectedStudentName] = useState<string | undefined>(undefined);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch at-risk students from backend.
  // Polling removed — the React Query cache is updated surgically by
  // useFacultyWebSocket when a `risk_score_updated` event is received
  // (via queryClient.setQueryData), and the query key is invalidated on
  // `attendance_verified` events.
  // A 5-minute background refresh is kept as a safety-net fallback.
  const { data: students = [], isLoading, isError, error } = useQuery({
    queryKey: ['at-risk-students'],
    queryFn: async () => {
      const response = await apiClient.get<AtRiskStudent[]>('/analytics/at-risk-students');
      return response.data;
    },
    retry: 1,
    refetchInterval: 300_000,
    staleTime: 60_000,
  });

  // Determine if failure is a model/inference failure vs generic network error
  const isModelFailure = isError && (() => {
    const status = (error as any)?.response?.status;
    return status === 503 || status === 500;
  })();

  const handleStudentClick = (studentId: string, studentName: string) => {
    setSelectedStudent(studentId);
    setSelectedStudentName(studentName);
    setIsModalOpen(true);
  };

  const getRiskColor = (riskLabel: string) => {
    switch (riskLabel) {
      case 'Critical':
        return { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300' };
      case 'At Risk':
        return { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300' };
      default:
        return { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-300' };
    }
  };

  const getRiskScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-red-600';
    if (score >= 0.5) return 'text-amber-600';
    return 'text-emerald-600';
  };

  return (
    <>
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          <h3 className="text-lg font-semibold text-slate-800">
            At-Risk Students ({students.length})
          </h3>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            {isModelFailure ? (
              <>
                <ServerCrash className="h-8 w-8 text-red-500" />
                <div className="text-center">
                  <p className="text-sm font-semibold text-red-700">Model Inference Failed</p>
                  <p className="text-xs text-slate-500 mt-1">
                    The XGBoost prediction engine is unavailable. No fallback data is shown.
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertCircle className="h-5 w-5 text-red-600" />
                <p className="text-sm text-red-600">Failed to load at-risk students</p>
              </>
            )}
          </div>
        ) : students.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-slate-500">No at-risk students detected</p>
          </div>
        ) : (
          <div className="space-y-2">
            {students.map((student) => {
              const colors = getRiskColor(student.riskLabel);
              return (
                <button
                  key={student.id}
                  onClick={() => handleStudentClick(student.id, student.name)}
                  className={`w-full flex items-center justify-between rounded-lg p-4 border transition-all hover:shadow-md active:scale-95 ${colors.bg} ${colors.border}`}
                >
                  <div className="flex items-center gap-4 flex-1 text-left">
                    <div className="flex-shrink-0">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white">
                        <AlertTriangle className={`h-5 w-5 ${colors.text}`} />
                      </div>
                    </div>
                    <div>
                      <p className={`font-semibold ${colors.text}`}>{student.name}</p>
                      {student.lastSeen && (
                        <p className="text-xs text-slate-600">Last seen: {student.lastSeen}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex flex-col items-end">
                      {/* Exact percentage — no rounding beyond 1 decimal place */}
                      <span className={`font-bold tabular-nums ${getRiskScoreColor(student.riskScore)}`}>
                        {(student.riskScore * 100).toFixed(1)}%
                      </span>
                      <span className={`text-xs font-medium ${colors.text}`}>
                        {student.riskLabel}
                      </span>
                    </div>
                    <ChevronRight className={`h-5 w-5 ${colors.text}`} />
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Risk Analysis Modal */}
      {selectedStudent && (
        <StudentRiskModal
          studentId={selectedStudent}
          studentName={selectedStudentName}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </>
  );
};
