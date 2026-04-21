import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { SHAPExplanationChart } from './SHAPExplanationChart';
import { X, Loader2, AlertCircle } from 'lucide-react';

interface SHAPExplanation {
  feature: string;
  value: number;
  shap_impact: number;
  human_readable: string;
}

interface StudentRiskPrediction {
  user_id: string;
  risk_label: number;
  risk_probability: number;
  shap_explanations: SHAPExplanation[];
}

interface StudentRiskModalProps {
  studentId: string;
  studentName?: string;
  isOpen: boolean;
  onClose: () => void;
}

export const StudentRiskModal: React.FC<StudentRiskModalProps> = ({
  studentId,
  studentName,
  isOpen,
  onClose,
}) => {
  const { data: prediction, isLoading, isError } = useQuery({
    queryKey: ['student-risk', studentId],
    queryFn: async () => {
      const response = await apiClient.post(`/analytics/predict/risk/${studentId}`);
      return response.data as StudentRiskPrediction;
    },
    enabled: isOpen && !!studentId,
    refetchOnWindowFocus: false,
  });

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-xl">
          {/* Header */}
          <div className="sticky top-0 flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Student Risk Analysis</h2>
              {studentName && (
                <p className="text-sm text-slate-600 mt-1">{studentName}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 hover:bg-slate-200 transition-colors"
            >
              <X className="h-5 w-5 text-slate-600" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {isLoading ? (
              <div className="flex h-96 items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
              </div>
            ) : isError || !prediction ? (
              <div className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-red-900">Unable to Load Risk Analysis</h4>
                  <p className="text-sm text-red-700 mt-1">
                    Please try again or contact an administrator if the problem persists.
                  </p>
                </div>
              </div>
            ) : (
              <SHAPExplanationChart
                explanations={prediction.shap_explanations}
                riskProbability={prediction.risk_probability}
              />
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-200 bg-slate-50 px-6 py-4">
            <button
              onClick={onClose}
              className="w-full rounded-lg bg-slate-100 px-4 py-2 font-medium text-slate-900 hover:bg-slate-200 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
