import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ClipboardCheck, CheckCircle2, XCircle, Loader2, AlertCircle, Sparkles, HelpCircle } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/shared/ui/Button';
import { toast } from 'sonner';
import type { VerificationTask, VerifyActionPayload, CurriculumGraph } from '@/types/faculty';

export const CurriculumVerificationQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTask, setActiveTask] = useState<{ task: VerificationTask; action: 'approve' | 'reject' | 'correct' } | null>(null);
  const [notes, setNotes] = useState('');
  const [correctedNode, setCorrectedNode] = useState<{ id: string; title: string } | null>(null);

  // Fetch pending verification tasks
  const { data: tasks = [], isLoading, isError } = useQuery({
    queryKey: ['curriculum-verification-queue'],
    queryFn: async () => {
      const response = await apiClient.get<VerificationTask[]>('/curriculum/verification-queue');
      return response.data;
    },
    refetchInterval: 60_000,
  });

  // Fetch curriculum graphs to support "Correct" action
  const { data: graphs = [] } = useQuery({
    queryKey: ['curriculum-graphs'],
    queryFn: async () => {
      const response = await apiClient.get<CurriculumGraph[]>('/curriculum/graphs');
      return response.data;
    },
  });

  const mutation = useMutation({
    mutationFn: async ({ taskId, payload }: { taskId: string; payload: VerifyActionPayload }) => {
      const response = await apiClient.post(`/curriculum/verify/${taskId}`, payload);
      return response.data;
    },
    onMutate: async ({ taskId }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['curriculum-verification-queue'] });

      // Snapshot previous state
      const previousTasks = queryClient.getQueryData<VerificationTask[]>(['curriculum-verification-queue']);

      // Optimistic update
      queryClient.setQueryData<VerificationTask[]>(['curriculum-verification-queue'], (old) =>
        old ? old.filter((task) => task.task_id !== taskId) : []
      );

      return { previousTasks };
    },
    onSuccess: (_, variables) => {
      toast.success(`Mapping ${variables.payload.action}ed successfully.`);
      setActiveTask(null);
      setNotes('');
      setCorrectedNode(null);
    },
    onError: (error: any, __, context) => {
      if (context?.previousTasks) {
        queryClient.setQueryData(['curriculum-verification-queue'], context.previousTasks);
      }
      toast.error('Failed to process verification', {
        description: error.response?.data?.detail || error.message || 'An error occurred.',
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['curriculum-verification-queue'] });
    },
  });

  const handleActionClick = (task: VerificationTask, action: 'approve' | 'reject' | 'correct') => {
    setActiveTask({ task, action });
    setNotes('');
    setCorrectedNode(null);
  };

  const handleSubmitAction = () => {
    if (!activeTask) return;

    const payload: VerifyActionPayload = {
      action: activeTask.action,
      notes: notes.trim() || undefined,
    };

    if (activeTask.action === 'correct') {
      if (!correctedNode) {
        toast.error('Please select the correct curriculum node');
        return;
      }
      payload.corrected_node_id = correctedNode.id;
      payload.corrected_node_title = correctedNode.title;
    }

    mutation.mutate({
      taskId: activeTask.task.task_id,
      payload,
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
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 flex flex-col items-center justify-center text-red-600">
        <AlertCircle className="h-8 w-8 mb-2" />
        <p className="font-semibold">Failed to load verification queue</p>
        <p className="text-sm">Please try again later.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-full">
      <div className="border-b border-slate-200 p-4 bg-slate-50 flex items-center gap-3">
        <ClipboardCheck className="h-6 w-6 text-indigo-600" />
        <div>
          <h2 className="text-lg font-bold text-slate-900">Curriculum Verification Queue</h2>
          <p className="text-sm text-slate-600">Review and resolve low-confidence topic mappings from local-LLM.</p>
        </div>
        <div className="ml-auto bg-indigo-100 text-indigo-800 text-xs font-bold px-3 py-1 rounded-full">
          {tasks.length} Pending
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3 py-12">
            <CheckCircle2 className="h-12 w-12 text-emerald-400 opacity-50" />
            <p className="font-medium text-lg">Queue Clear</p>
            <p className="text-sm">All curriculum mappings are verified or above threshold.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {tasks.map((task) => (
              <div key={task.task_id} className="border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all bg-white">
                <div className="flex justify-between items-start mb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Extracted Topic</span>
                      <span className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 border border-indigo-100">
                        <Sparkles className="w-3 h-3 mr-1" />
                        LLM Confidence: {(task.topic_confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <h3 className="text-xl font-bold text-slate-900 italic">"{task.topic}"</h3>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Similarity Score</p>
                    <p className={`text-lg font-mono font-bold ${task.similarity_score < 0.5 ? 'text-red-500' : 'text-amber-500'}`}>
                      {task.similarity_score.toFixed(4)}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                    <p className="text-xs font-bold text-slate-500 uppercase mb-2">Suggested Mapping</p>
                    <p className="text-sm font-semibold text-slate-800">{task.original_node_title}</p>
                    <p className="text-xs text-slate-500 font-mono mt-1">{task.original_node_id}</p>
                  </div>
                  <div className="bg-indigo-50/30 rounded-lg p-3 border border-indigo-100">
                    <p className="text-xs font-bold text-indigo-500 uppercase mb-2">Context</p>
                    <p className="text-sm text-slate-700">Session: <span className="font-semibold">{task.session_id}</span></p>
                    <p className="text-sm text-slate-700">Course: <span className="font-semibold">{task.course_id}</span></p>
                  </div>
                </div>

                {activeTask?.task.task_id === task.task_id ? (
                  <div className="bg-slate-50 p-4 rounded-xl border border-indigo-200 animate-in fade-in zoom-in-95 duration-200">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="h-2 w-2 rounded-full bg-indigo-600 animate-pulse" />
                      <p className="text-sm font-bold text-slate-800 uppercase tracking-tight">
                        Action: {activeTask.action}
                      </p>
                    </div>

                    {activeTask.action === 'correct' && (
                      <div className="mb-4">
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Select Correct Node</label>
                        <select 
                          className="w-full text-sm border-slate-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 p-2.5 bg-white shadow-sm"
                          onChange={(e) => {
                            const [id, title] = e.target.value.split('|');
                            setCorrectedNode({ id, title });
                          }}
                        >
                          <option value="">-- Choose correct node --</option>
                          {graphs.flatMap(g => g.nodes || []).filter(Boolean).map(node => (
                            <option key={node.id} value={`${node.id}|${node.title}`}>
                              {node.title} ({node.id})
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    <div className="mb-4">
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Notes / Justification</label>
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="e.g. Topic is actually part of Module 3 introductory lecture."
                        className="w-full text-sm border-slate-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 p-3 bg-white shadow-sm"
                        rows={2}
                      />
                    </div>

                    <div className="flex gap-2 justify-end">
                      <Button variant="outline" onClick={() => setActiveTask(null)} disabled={mutation.isPending}>
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleSubmitAction} 
                        disabled={mutation.isPending || (activeTask.action === 'correct' && !correctedNode)}
                        className={
                          activeTask.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 
                          activeTask.action === 'reject' ? 'bg-red-600 hover:bg-red-700' : 
                          'bg-indigo-600 hover:bg-indigo-700'
                        }
                      >
                        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        Confirm {activeTask.action.charAt(0).toUpperCase() + activeTask.action.slice(1)}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      className="flex-1 text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                      onClick={() => handleActionClick(task, 'approve')}
                    >
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Approve
                    </Button>
                    <Button
                      variant="outline"
                      className="flex-1 text-indigo-600 border-indigo-200 hover:bg-indigo-50"
                      onClick={() => handleActionClick(task, 'correct')}
                    >
                      <HelpCircle className="w-4 h-4 mr-2" />
                      Correct
                    </Button>
                    <Button
                      variant="outline"
                      className="flex-1 text-red-600 border-red-200 hover:bg-red-50"
                      onClick={() => handleActionClick(task, 'reject')}
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
