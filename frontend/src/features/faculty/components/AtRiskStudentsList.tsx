import React, { useState } from 'react';
import { AlertTriangle, ChevronRight } from 'lucide-react';
import { StudentRiskModal } from './StudentRiskModal';

interface AtRiskStudent {
  id: string;
  name: string;
  riskScore: number;
  riskLabel: 'Safe' | 'At Risk' | 'Critical';
  lastSeen?: string;
}

interface AtRiskStudentsListProps {
  students?: AtRiskStudent[];
  isLoading?: boolean;
}

export const AtRiskStudentsList: React.FC<AtRiskStudentsListProps> = ({
  students = [
    {
      id: 'student_001',
      name: 'Rajesh Kumar',
      riskScore: 0.78,
      riskLabel: 'Critical',
      lastSeen: '2 hours ago',
    },
    {
      id: 'student_002',
      name: 'Priya Singh',
      riskScore: 0.62,
      riskLabel: 'At Risk',
      lastSeen: '5 minutes ago',
    },
    {
      id: 'student_003',
      name: 'Amit Patel',
      riskScore: 0.55,
      riskLabel: 'At Risk',
      lastSeen: '1 hour ago',
    },
  ],
  isLoading = false,
}) => {
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleStudentClick = (studentId: string) => {
    setSelectedStudent(studentId);
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

  const selectedStudentName = students.find(s => s.id === selectedStudent)?.name;

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
            <div className="text-slate-500">Loading...</div>
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
                  onClick={() => handleStudentClick(student.id)}
                  className={`w-full flex items-center justify-between rounded-lg p-4 border transition-all hover:shadow-md active:scale-95 ${colors.bg} ${colors.border} border`}
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
                      <span className={`font-bold ${getRiskScoreColor(student.riskScore)}`}>
                        {(student.riskScore * 100).toFixed(0)}%
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
