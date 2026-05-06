import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { PredictiveAnalyticsDashboard } from '../components';

import { AlertCircle } from 'lucide-react';

export const PredictiveAnalyticsPage: React.FC = () => {
  const { data: activeSessions, isLoading, isError } = useQuery({
    queryKey: ['faculty-live-sessions-analytics'],
    queryFn: async () => {
      const response = await apiClient.get<any[]>('/attendance/sessions');
      return response.data;
    },
    staleTime: 30_000,
  });

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] rounded-[2rem] border border-red-100 bg-red-50/50 p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-100 text-red-600 mb-4">
          <AlertCircle className="h-8 w-8" />
        </div>
        <h3 className="text-xl font-semibold text-red-900">Service Unavailable</h3>
        <p className="mt-2 text-red-600 max-w-md">
          The ML analytics engine is currently unreachable. 
          Please ensure the local FastAPI backend is online.
        </p>
      </div>
    );
  }

  const sessionId = activeSessions?.[0]?.id ?? null;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
          Predictive analytics dashboard
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-900">
          ML-powered student risk assessment and explanations
        </h2>
      </div>

      <div className="rounded-[1.75rem] border border-slate-200 bg-white overflow-hidden shadow-sm">
        <PredictiveAnalyticsDashboard sessionId={sessionId} />
      </div>
    </div>
  );
};
