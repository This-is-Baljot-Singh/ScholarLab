import React, { useState } from 'react';
import { Play, Square, ChevronRight } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import type { LiveSession, SessionInitPayload, CurriculumGraph, GeofenceWithMetadata } from '@/types/faculty';

// Type guards
const isCircleGeofence = (geofence: GeofenceWithMetadata): geofence is GeofenceWithMetadata & { type: 'circle'; radiusMeters: number } => {
  return 'type' in geofence && geofence.type === 'circle';
};

const isPolygonGeofence = (geofence: GeofenceWithMetadata): geofence is GeofenceWithMetadata & { type: 'polygon'; coordinates: any[] } => {
  return 'type' in geofence && geofence.type === 'polygon';
};

interface SessionInitializerProps {
  activeSessions: LiveSession[];
  graphs: CurriculumGraph[];
  geofences: GeofenceWithMetadata[];
  onStartSession: (payload: SessionInitPayload) => void;
  onEndSession: (sessionId: string) => void;
}

export const SessionInitializer: React.FC<SessionInitializerProps> = ({
  activeSessions,
  graphs,
  geofences,
  onStartSession,
  onEndSession,
}) => {
  const [form, setForm] = useState<SessionInitPayload>({
    lectureId: `lecture-${Date.now()}`,
    curriculumNodeId: '',
    geofenceId: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleStartSession = async () => {
    if (!form.curriculumNodeId || !form.geofenceId) {
      alert('Please select both a curriculum node and geofence');
      return;
    }

    setIsSubmitting(true);
    try {
      onStartSession(form);
      setForm({
        lectureId: `lecture-${Date.now()}`,
        curriculumNodeId: '',
        geofenceId: '',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Find selected graph and node details
  const selectedGraph = graphs.find((g) =>
    g.nodes.some((n) => n.id === form.curriculumNodeId)
  );
  const selectedNode = selectedGraph?.nodes.find((n) => n.id === form.curriculumNodeId);
  const selectedGeofence = geofences.find((g) => g.id === form.geofenceId);

  return (
    <div className="h-screen bg-slate-50 flex">
      {/* Main Panel */}
      <div className="flex-1 flex flex-col">
        <div className="bg-white border-b border-slate-200 p-6">
          <h1 className="text-2xl font-bold text-slate-900">Session Initialization</h1>
          <p className="text-slate-600 text-sm mt-1">Start a live class session with curriculum and geofence assignment</p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Session Form */}
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Start New Session</h2>

              <div className="grid grid-cols-2 gap-6">
                {/* Curriculum Selection */}
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-3">
                    Curriculum Topic
                  </label>
                  {graphs.length === 0 ? (
                    <div className="p-4 bg-slate-50 rounded border border-slate-200 text-sm text-slate-600">
                      No curriculum graphs created yet. Create one first in the Graph Builder.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {graphs.flatMap((graph) => (
                        <div key={graph.id} className="border border-slate-200 rounded-lg overflow-hidden">
                          <div className="bg-slate-50 px-4 py-2 border-b border-slate-200">
                            <p className="text-sm font-semibold text-slate-900">{graph.title}</p>
                          </div>
                          <div className="bg-white p-0">
                            {graph.nodes.map((node) => (
                              <button
                                key={node.id}
                                onClick={() => setForm({ ...form, curriculumNodeId: node.id })}
                                className={`w-full p-3 border-b border-slate-100 last:border-b-0 text-left transition-colors ${
                                  form.curriculumNodeId === node.id
                                    ? 'bg-indigo-50 border-l-4 border-l-indigo-600'
                                    : 'hover:bg-slate-50'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex-1 min-w-0">
                                    <p className="font-medium text-slate-900 text-sm">{node.title}</p>
                                    {node.description && (
                                      <p className="text-xs text-slate-600 mt-0.5 line-clamp-1">
                                        {node.description}
                                      </p>
                                    )}
                                    {node.difficulty && (
                                      <span className={`inline-block text-xs mt-1 px-2 py-0.5 rounded font-medium ${
                                        node.difficulty === 'beginner'
                                          ? 'bg-green-100 text-green-800'
                                          : node.difficulty === 'intermediate'
                                            ? 'bg-yellow-100 text-yellow-800'
                                            : 'bg-red-100 text-red-800'
                                      }`}>
                                        {node.difficulty}
                                      </span>
                                    )}
                                  </div>
                                  <ChevronRight className={`w-4 h-4 ml-2 transition-all ${
                                    form.curriculumNodeId === node.id ? 'text-indigo-600' : 'text-slate-400'
                                  }`} />
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Geofence Selection */}
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-3">
                    Teaching Location (Geofence)
                  </label>
                  {geofences.length === 0 ? (
                    <div className="p-4 bg-slate-50 rounded border border-slate-200 text-sm text-slate-600">
                      No geofences created yet. Create one first in the Geofence Manager.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-2">
                      {geofences.map((geofence) => (
                        <button
                          key={geofence.id}
                          onClick={() => setForm({ ...form, geofenceId: geofence.id })}
                          className={`p-3 rounded-lg border-2 transition-all text-left ${
                            form.geofenceId === geofence.id
                              ? 'border-indigo-500 bg-indigo-50'
                              : 'border-slate-200 bg-white hover:border-slate-300'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-slate-900">{geofence.name}</p>
                              {geofence.buildingCode && (
                                <p className="text-xs text-slate-600 mt-0.5">{geofence.buildingCode}</p>
                              )}
                              <p className="text-xs text-slate-500 mt-1">
                                {isCircleGeofence(geofence)
                                  ? `● Circle - ${geofence.radiusMeters}m radius`
                                  : isPolygonGeofence(geofence)
                                    ? `⬠ Polygon - ${geofence.coordinates.length} points`
                                    : 'Unknown type'}
                              </p>
                            </div>
                            <ChevronRight className={`w-5 h-5 transition-all ${
                              form.geofenceId === geofence.id ? 'text-indigo-600' : 'text-slate-400'
                            }`} />
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Start Button */}
              <div className="mt-6 pt-6 border-t border-slate-200">
                <Button
                  onClick={handleStartSession}
                  disabled={isSubmitting || !form.curriculumNodeId || !form.geofenceId}
                  className="w-full"
                  size="lg"
                >
                  <Play className="w-5 h-5 mr-2" />
                  {isSubmitting ? 'Starting Session...' : 'Start Live Session'}
                </Button>
              </div>
            </div>

            {/* Session Preview */}
            {selectedNode && selectedGeofence && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-6">
                <h3 className="font-semibold text-slate-900 mb-4">Session Preview</h3>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <p className="text-xs font-medium text-slate-700 mb-1">Curriculum Topic</p>
                    <p className="text-lg font-semibold text-slate-900">{selectedNode.title}</p>
                    {selectedNode.difficulty && (
                      <p className="text-sm text-slate-600 mt-2">
                        Difficulty: <span className="font-medium">{selectedNode.difficulty}</span>
                      </p>
                    )}
                    {selectedNode.estimatedHours && (
                      <p className="text-sm text-slate-600">
                        Duration: <span className="font-medium">{selectedNode.estimatedHours}h</span>
                      </p>
                    )}
                    {selectedNode.resources.length > 0 && (
                      <div className="mt-3">
                        <p className="text-sm font-medium text-slate-700 mb-2">Resources</p>
                        <ul className="space-y-1">
                          {selectedNode.resources.map((rsrc) => (
                            <li key={rsrc.id} className="text-sm text-slate-600 flex items-center gap-2">
                              <span className="text-xs">📦</span>
                              {rsrc.title}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-700 mb-1">Teaching Location</p>
                    <p className="text-lg font-semibold text-slate-900">{selectedGeofence.name}</p>
                    {selectedGeofence.buildingCode && (
                      <p className="text-sm text-slate-600 mt-2">Code: {selectedGeofence.buildingCode}</p>
                    )}
                    <p className="text-sm text-slate-600 mt-2">
                      {selectedGeofence.type === 'circle'
                        ? `Radius: ${selectedGeofence.radiusMeters}m`
                        : `Points: ${selectedGeofence.coordinates.length}`}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Active Sessions Sidebar */}
      <div className="w-80 bg-white border-l border-slate-200 flex flex-col">
        <div className="border-b border-slate-200 p-4">
          <h3 className="font-semibold text-slate-900">Active Sessions</h3>
          <p className="text-xs text-slate-600 mt-1">{activeSessions.length} session(s) running</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {activeSessions.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-slate-600">No active sessions</p>
            </div>
          ) : (
            activeSessions.map((session) => (
              <div
                key={session.id}
                className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-lg p-3"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-900 text-sm">{session.lectureId}</p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      {new Date(session.startTime).toLocaleTimeString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 ml-2">
                    <div className="w-2 h-2 rounded-full bg-green-600 animate-pulse" />
                    <span className="text-xs font-medium text-green-700">LIVE</span>
                  </div>
                </div>

                <div className="text-xs text-slate-700 mb-2">
                  <p>👥 {session.attendanceCount} students</p>
                </div>

                <Button
                  onClick={() => onEndSession(session.id)}
                  variant="destructive"
                  size="sm"
                  className="w-full"
                >
                  <Square className="w-3 h-3 mr-2" />
                  End Session
                </Button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
