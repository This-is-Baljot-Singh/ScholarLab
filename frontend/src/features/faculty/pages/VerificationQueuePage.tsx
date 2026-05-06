import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { AuditQueuePanel, CurriculumVerificationQueue } from '../components';
import { toast } from 'sonner';

export const VerificationQueuePage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: curriculumQueue, isLoading, isError } = useQuery({
    queryKey: ['curriculum-verification-queue'],
    queryFn: async () => {
      const response = await apiClient.get('/curriculum/verification-queue');
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
          The curriculum verification service is currently unreachable. 
          Please check the backend status.
        </p>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
          Manual Verification Queues
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-900">
          Review and resolve flagged items
        </h2>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <p className="text-sm font-bold text-slate-500 uppercase tracking-widest">Attendance Anomalies</p>
          <AuditQueuePanel />
        </div>
        <div className="space-y-4">
          <p className="text-sm font-bold text-slate-500 uppercase tracking-widest">Curriculum Mapping</p>
          <CurriculumVerificationQueue />
        </div>
      </div>
    </div>
  );
};
