import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldAlert, CheckCircle2, XCircle, Loader2, AlertCircle, Clock } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/shared/ui/Button';
import { toast } from 'sonner';
import type { AuditQueueRecord, AuditActionPayload } from '@/types/faculty';

export const AuditQueuePanel: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeAction, setActiveAction] = useState<{ id: string; approve: boolean } | null>(null);
  const [justification, setJustification] = useState('');

  const { data: queue = [], isLoading, isError } = useQuery({
    queryKey: ['audit-queue'],
    queryFn: async () => {
      const response = await apiClient.get<AuditQueueRecord[]>('/attendance/audit-queue');
      return response.data;
    },
    refetchInterval: 30_000, // Refresh every 30 seconds
  });

  const mutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: AuditActionPayload }) => {
      const response = await apiClient.post(`/attendance/audit/${id}`, payload);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['audit-queue'] });
      toast.success(`Audit record ${variables.payload.approve ? 'approved' : 'rejected'} successfully.`);
      setActiveAction(null);
      setJustification('');
    },
    onError: (error: any) => {
      toast.error('Failed to process audit', {
        description: error.response?.data?.detail || error.message || 'An error occurred.',
      });
    },
  });

  const handleActionClick = (id: string, approve: boolean) => {
    setActiveAction({ id, approve });
    setJustification('');
  };

  const handleSubmitAction = () => {
    if (!activeAction) return;
    if (!justification.trim()) {
      toast.error('Justification is required');
      return;
    }
    mutation.mutate({
      id: activeAction.id,
      payload: {
        approve: activeAction.approve,
        justification: justification.trim(),
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex flex-col items-center justify-center text-red-600">
        <AlertCircle className="h-8 w-8 mb-2" />
        <p className="font-semibold">Failed to load audit queue</p>
        <p className="text-sm">Please try again later.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-full">
      <div className="border-b border-slate-200 p-4 bg-slate-50 flex items-center gap-3">
        <ShieldAlert className="h-6 w-6 text-amber-600" />
        <div>
          <h2 className="text-lg font-bold text-slate-900">Anti-Spoofing Audit Queue</h2>
          <p className="text-sm text-slate-600">Review attendance records flagged for moderate confidence.</p>
        </div>
        <div className="ml-auto bg-amber-100 text-amber-800 text-xs font-bold px-3 py-1 rounded-full">
          {queue.length} Pending
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {queue.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3 py-12">
            <CheckCircle2 className="h-12 w-12 text-emerald-400 opacity-50" />
            <p className="font-medium text-lg">No pending audits</p>
            <p className="text-sm">All flagged records have been processed.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {queue.map((record) => (
              <div key={record.id} className="border border-slate-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow bg-white flex flex-col">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{record.studentName}</h3>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">{record.studentId}</p>
                  </div>
                  <div className="flex items-center text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded">
                    <Clock className="w-3 h-3 mr-1" />
                    {new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded p-2 mb-4">
                  <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-1">Flag Reason</p>
                  <p className="text-sm text-amber-900">
                    {record.metadata.flag_reason || 'Unknown anomaly'}
                  </p>
                </div>

                <div className="mt-auto">
                  {activeAction?.id === record.id ? (
                    <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 animate-in fade-in slide-in-from-bottom-2">
                      <p className="text-xs font-medium text-slate-700 mb-2">
                        {activeAction.approve ? 'Approve' : 'Reject'} Justification (Required)
                      </p>
                      <textarea
                        value={justification}
                        onChange={(e) => setJustification(e.target.value)}
                        placeholder="e.g. Student confirmed present in person"
                        className="w-full text-sm border-slate-300 rounded focus:ring-indigo-500 focus:border-indigo-500 mb-2 p-2"
                        rows={2}
                        autoFocus
                      />
                      <div className="flex gap-2 justify-end">
                        <Button variant="outline" size="sm" onClick={() => setActiveAction(null)} disabled={mutation.isPending}>
                          Cancel
                        </Button>
                        <Button 
                          size="sm" 
                          onClick={handleSubmitAction} 
                          disabled={mutation.isPending || !justification.trim()}
                          className={activeAction.approve ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}
                        >
                          {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Confirm'}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        className="flex-1 text-emerald-600 border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700"
                        onClick={() => handleActionClick(record.id, true)}
                      >
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                        Approve
                      </Button>
                      <Button
                        variant="outline"
                        className="flex-1 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                        onClick={() => handleActionClick(record.id, false)}
                      >
                        <XCircle className="w-4 h-4 mr-2" />
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
