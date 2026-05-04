import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { SessionInitializer } from '../components';
import { SessionCloseModal } from '../components';
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
  // ── Active sessions ──────────────────────────────────────────────────────
  const [activeSessions, setActiveSessions] = useState<LiveSession[]>([
    {
      id: 'session-1',
      lectureId: 'lecture-morning',
      currentCurriculumNodeId: 'node-1',
      geofenceId: 'geofence-1',
      facultyId: 'faculty-1',
      startTime: new Date().toISOString(),
      status: 'active',
      attendanceCount: 24,
    },
  ]);

  // ── Curriculum graphs (mock; replace with useQuery once backend is wired) ─
  const [graphs] = useState<CurriculumGraph[]>([
    {
      id: 'graph-1',
      title: 'Data Structures Course',
      description: 'Complete data structures curriculum',
      nodes: [
        {
          id: 'node-1',
          title: 'Arrays & Lists',
          description: 'Introduction to arrays and linked lists',
          difficulty: 'beginner',
          estimatedHours: 2,
          resources: [
            {
              id: 'res-1',
              title: 'Lecture Slides',
              type: 'pdf',
              uri: 'https://example.com/slides.pdf',
              createdAt: new Date().toISOString(),
            },
          ],
          prerequisites: [],
        },
        {
          id: 'node-2',
          title: 'Binary Trees',
          description: 'Tree structures and traversals',
          difficulty: 'intermediate',
          estimatedHours: 3,
          resources: [],
          prerequisites: ['node-1'],
        },
        {
          id: 'node-3',
          title: 'Advanced Tree Algorithms',
          description: 'AVL and Red-Black trees',
          difficulty: 'advanced',
          estimatedHours: 4,
          resources: [],
          prerequisites: ['node-2'],
        },
      ],
      edges: [
        { source: 'node-1', target: 'node-2' },
        { source: 'node-2', target: 'node-3' },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  ]);

  // ── Geofences ────────────────────────────────────────────────────────────
  const [geofences] = useState<GeofenceWithMetadata[]>([
    {
      type: 'circle',
      center: { latitude: 40.1105, longitude: -88.2073 },
      radiusMeters: 150,
      id: 'geofence-1',
      name: 'Engineering Hall',
      buildingCode: 'ENG-101',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    {
      type: 'circle',
      center: { latitude: 40.112, longitude: -88.21 },
      radiusMeters: 200,
      id: 'geofence-2',
      name: 'Science Building',
      buildingCode: 'SCI-200',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  ]);

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

  const handleStartSession = (payload: SessionInitPayload) => {
    const newSession: LiveSession = {
      id: `session-${Date.now()}`,
      lectureId: payload.lectureId,
      currentCurriculumNodeId: payload.curriculumNodeId,
      geofenceId: payload.geofenceId,
      facultyId: 'faculty-1',
      startTime: new Date().toISOString(),
      status: 'active',
      attendanceCount: 0,
    };
    setActiveSessions((prev) => [...prev, newSession]);
    toast.success(`Session started! Lecture ID: ${payload.lectureId}`);
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
    setActiveSessions((prev) =>
      prev.filter((s) => s.id !== sessionPendingClose.id),
    );
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
