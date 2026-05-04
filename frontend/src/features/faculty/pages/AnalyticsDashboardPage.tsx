import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { PredictiveAnalyticsDashboard } from '../components';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';

interface AnalyticsDashboardPageProps {
  onBack: () => void;
}

export const AnalyticsDashboardPage: React.FC<AnalyticsDashboardPageProps> = ({ onBack }) => {
  // Fetch the faculty's most recently active session to provide a session_id to
  // the WebSocket. This is Option B from the implementation plan: auto-fetch
  // rather than requiring a URL param change. The query is lightweight — it
  // only runs once on mount and does not poll.
  const { data: activeSession } = useQuery({
    queryKey: ['active-session'],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ id: string; status: string }[]>('/analytics/sessions/active');
        return response.data?.[0] ?? null;
      } catch {
        // Gracefully degrade: if the endpoint doesn't exist yet, return null
        // and the dashboard works without live WS updates.
        return null;
      }
    },
    staleTime: Infinity, // Session ID doesn't change while viewing the dashboard
    retry: false,
  });

  const sessionId = activeSession?.id ?? null;

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
      <div className="flex-1 overflow-y-auto bg-slate-50">
        <PredictiveAnalyticsDashboard sessionId={sessionId} />
      </div>
    </div>
  );
};
