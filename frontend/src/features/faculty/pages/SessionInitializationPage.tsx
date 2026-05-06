import React, { useState } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/shared/ui/Button';
import { SessionInitializer } from '../components';
import { SessionCloseModal } from '../components';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';
import type {
  LiveSession,
  SessionInitPayload,
  CurriculumGraph,
  GeofenceWithMetadata,
} from '@/types/faculty';

interface SessionInitializationPageProps {
  onBack: () => void;
}

export const SessionInitializationPage: React.FC<SessionInitializationPageProps> = ({
  onBack,
}) => {
  const queryClient = useQueryClient();

  // ── Active sessions ──────────────────────────────────────────────────────
  const { data: activeSessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ['active-sessions'],
    queryFn: async () => {
      const response = await apiClient.get<LiveSession[]>('/curriculum/sessions/active');
      return response.data;
    },
    refetchInterval: 10_000,
  });

  // ── Curriculum graphs ────────────────────────────────────────────────────
  const { data: graphs = [], isLoading: graphsLoading } = useQuery({
    queryKey: ['curriculum-graphs'],
    queryFn: async () => {
      const response = await apiClient.get<CurriculumGraph[]>('/curriculum/graphs');
      return response.data;
    },
  });

  // ── Geofences ────────────────────────────────────────────────────────────
  const { data: geofences = [], isLoading: geofencesLoading } = useQuery({
    queryKey: ['geofences'],
    queryFn: async () => {
      const response = await apiClient.get<GeofenceWithMetadata[]>('/geofences');
      return response.data;
    },
  });

  // ── Session-Close Modal state ─────────────────────────────────────────────
  /**
   * When faculty clicks "End Session" on an active session card, we store the
   * session here instead of immediately removing it. The SessionCloseModal
   * opens, faculty selects covered nodes, then fires the API. Only after a
   * successful response do we remove the session from the active list.
   */
  const [sessionPendingClose, setSessionPendingClose] = useState<LiveSession | null>(
    null,
  );

  // ── Helpers ───────────────────────────────────────────────────────────────

  const startSessionMutation = useMutation({
    mutationFn: async (payload: SessionInitPayload) => {
      const response = await apiClient.post('/curriculum/sessions', payload);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['active-sessions'] });
      toast.success(`Session started! Lecture ID: ${data.lectureId}`);
    },
    onError: (error: any) => {
      toast.error('Failed to start session', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });

  const handleStartSession = (payload: SessionInitPayload) => {
    startSessionMutation.mutate(payload);
  };

  /**
   * Intercept the End Session action — open the SessionCloseModal instead of
   * immediately removing the session from state. The session is only removed
   * after the faculty confirms and the API call succeeds (handleCloseConfirm).
   */
  const handleEndSession = (sessionId: string) => {
    const session = activeSessions.find((s) => s.id === sessionId);
    if (session) {
      setSessionPendingClose(session);
    }
  };

  /** Called by SessionCloseModal after a successful POST to the backend */
  const handleCloseConfirm = () => {
    if (!sessionPendingClose) return;
    const attendanceCount = sessionPendingClose.attendanceCount;
    queryClient.invalidateQueries({ queryKey: ['active-sessions'] });
    toast.success(
      `Session closed. Final attendance: ${attendanceCount} student${
        attendanceCount !== 1 ? 's' : ''
      }`,
    );
    setSessionPendingClose(null);
  };

  /** Called when faculty cancels the modal — session stays active */
  const handleCloseCancel = () => {
    setSessionPendingClose(null);
  };

  // Find the curriculum graph associated with the session being closed
  const graphForClosingSession = sessionPendingClose
    ? (graphs.find((g) =>
        g.nodes.some((n) => n.id === sessionPendingClose.currentCurriculumNodeId),
      ) ?? graphs[0] ?? null)
    : null;

  // ── Render ────────────────────────────────────────────────────────────────

  if (sessionsLoading || graphsLoading || geofencesLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-slate-600 font-medium">Loading session infrastructure...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <Button onClick={onBack} variant="ghost" size="sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Session Initialization</h1>
          <p className="text-slate-600 text-sm mt-1">
            Start live classes and manage attendance verification geofences
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <SessionInitializer
          activeSessions={activeSessions}
          graphs={graphs}
          geofences={geofences}
          onStartSession={handleStartSession}
          onEndSession={handleEndSession}
        />
      </div>

      {/* Session-Close Modal — rendered only when a session is pending close */}
      {sessionPendingClose && graphForClosingSession && (
        <SessionCloseModal
          sessionId={sessionPendingClose.id}
          graph={graphForClosingSession}
          preCompletedNodeIds={[]}
          isOpen={true}
          onCancel={handleCloseCancel}
          onConfirm={handleCloseConfirm}
        />
      )}
    </div>
  );
};
