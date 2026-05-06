import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { SHAPExplanationChart } from './SHAPExplanationChart';
import { X, Loader2, AlertCircle, ServerCrash, UserX, ExternalLink } from 'lucide-react';

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
  const { data: prediction, isLoading, isError, error } = useQuery({
    queryKey: ['student-risk', studentId],
    queryFn: async () => {
      const response = await apiClient.post(`/analytics/predict/risk/${studentId}`);
      return response.data as StudentRiskPrediction;
    },
    enabled: isOpen && !!studentId,
    retry: 0,  // No silent retries — surface failures immediately
    refetchOnWindowFocus: false,
  });

  // Classify the failure type so we can show precise error copy
  const errorStatus: number | null = isError
    ? ((error as any)?.response?.status ?? null)
    : null;

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
              <div className="flex gap-3 rounded-lg border p-4 bg-red-50 border-red-200">
                {errorStatus === 503 ? (
                  <>
                    <ServerCrash className="h-6 w-6 flex-shrink-0 text-red-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-red-900">Model Inference Failed</h4>
                      <p className="text-sm text-red-700 mt-1">
                        The XGBoost prediction engine is offline. No risk analysis
                        can be displayed. Contact your administrator to restart the
                        inference service.
                      </p>
                    </div>
                  </>
                ) : errorStatus === 404 ? (
                  <>
                    <UserX className="h-6 w-6 flex-shrink-0 text-amber-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-amber-900">Student Not Found</h4>
                      <p className="text-sm text-amber-700 mt-1">
                        No feature vector could be built for this student.
                        They may not have any attendance records yet.
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-6 w-6 flex-shrink-0 text-red-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-red-900">Model Inference Failed</h4>
                      <p className="text-sm text-red-700 mt-1">
                        The backend could not compute a valid XGBoost feature
                        vector for this student. No fallback data is shown.
                      </p>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <SHAPExplanationChart
                explanations={prediction.shap_explanations}
                riskProbability={prediction.risk_probability}
              />
            )}
          </div>

          {/* Footer */}
          <div className="flex gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4">
            <button
              onClick={onClose}
              className="flex-1 rounded-lg bg-white border border-slate-200 px-4 py-2 font-medium text-slate-900 hover:bg-slate-50 transition-colors"
            >
              Close
            </button>
            <Link
              to={`/faculty/students/${studentId}`}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              View Full Profile
              <ExternalLink className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </>
  );
};
