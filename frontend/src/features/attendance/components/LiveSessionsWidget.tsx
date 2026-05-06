/**
 * LiveSessionsWidget - Displays today's active/upcoming sessions
 * Fetches from GET /api/attendance/sessions with graceful fallback to mock data
 */

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Clock, MapPin, AlertCircle } from 'lucide-react';
import { attendanceAPI } from '@/api/studentAPI';
import { SkeletonLoader } from '@/shared/ui/SkeletonLoader';
import { Button } from '@/shared/ui/Button';
import { useStudentDashboardStore } from '@/store/dashboardStore';
import type { AttendanceSession } from '@/types/dashboard';
import { cn } from '@/lib/utils';

// Mock data fallback
const MOCK_SESSIONS: AttendanceSession[] = [
  {
    id: 'session-001',
    lectureId: 'lecture-cs101',
    title: 'CS101: Introduction to Computer Science',
    instructor: 'Dr. Sarah Chen',
    startTime: new Date().toISOString(),
    endTime: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    location: 'Science Building, Room 201',
    classCode: 'CS101-001',
    status: 'ongoing',
    geofenceLatitude: 37.7749,
    geofenceLongitude: -122.4194,
    geofenceRadius: 50,
  },
  {
    id: 'session-002',
    lectureId: 'lecture-cs203',
    title: 'CS203: Data Structures & Algorithms',
    instructor: 'Prof. James Mitchell',
    startTime: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    endTime: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(),
    location: 'Science Building, Room 305',
    classCode: 'CS203-002',
    status: 'upcoming',
    geofenceLatitude: 37.7749,
    geofenceLongitude: -122.4194,
    geofenceRadius: 50,
  },
];

interface LiveSessionsWidgetProps {
  onSelectSession?: (session: AttendanceSession) => void;
}

export const LiveSessionsWidget: React.FC<LiveSessionsWidgetProps> = ({
  onSelectSession,
}) => {
  const setSelectedSessionId = useStudentDashboardStore(
    (s) => s.setSelectedSessionId
  );
  const setShowAttendanceModal = useStudentDashboardStore(
    (s) => s.setShowAttendanceModal
  );

  // Fetch sessions with fallback to mock data
  const { data: sessions, isLoading, error } = useQuery({
    queryKey: ['attendance', 'sessions'],
    queryFn: attendanceAPI.getSessions,
    staleTime: 1000 * 60 * 2, // 2 minutes
    retry: 2,
  });

  // Use mock data as fallback if API fails
  const displaySessions = useMemo(() => {
    if (sessions) return sessions;
    if (error && !isLoading) {
      console.warn(
        'Failed to load sessions from API, using mock data:',
        error
      );
      return MOCK_SESSIONS;
    }
    return [];
  }, [sessions, error, isLoading]);

  const handleMarkAttendance = (session: AttendanceSession) => {
    setSelectedSessionId(session.id);
    setShowAttendanceModal(true);
    onSelectSession?.(session);
  };

  if (isLoading && !sessions) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-6 text-lg font-semibold text-slate-900">
          Live Sessions Today
        </h2>
        <div className="space-y-4">
          <SkeletonLoader height="h-24" count={2} />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">
          Live Sessions Today
        </h2>
        {error && !sessions && (
          <div className="flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-1.5">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <span className="text-xs text-amber-700">Using mock data</span>
          </div>
        )}
      </div>

      {displaySessions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 py-8 text-center">
          <p className="text-sm text-slate-500">
            No sessions scheduled for today
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {displaySessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              onMarkAttendance={() => handleMarkAttendance(session)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Individual session card component
 */
interface SessionCardProps {
  session: AttendanceSession;
  onMarkAttendance: () => void;
}

const SessionCard: React.FC<SessionCardProps> = ({
  session,
  onMarkAttendance,
}) => {
  const startTime = new Date(session.startTime);
  const endTime = new Date(session.endTime);

  const statusStyles = {
    ongoing:
      'bg-green-50 border-green-200 text-green-700 ring-1 ring-green-600/20',
    upcoming:
      'bg-blue-50 border-blue-200 text-blue-700 ring-1 ring-blue-600/20',
    completed: 'bg-slate-50 border-slate-200 text-slate-600',
  };

  return (
    <div
      className={cn(
        'rounded-lg border-2 p-4 transition-all hover:shadow-md',
        statusStyles[session.status]
      )}
    >
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-slate-900">{session.title}</h3>
          <p className="text-sm text-slate-600">{session.instructor}</p>
        </div>
        <span
          className={cn(
            'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
            session.status === 'ongoing'
              ? 'bg-green-100 text-green-700'
              : session.status === 'upcoming'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-slate-100 text-slate-700'
          )}
        >
          {session.status === 'ongoing' && (
            <>
              <span className="mr-1.5 inline-block h-2 w-2 animate-pulse rounded-full bg-green-600" />
              Live
            </>
          )}
          {session.status === 'upcoming' && 'Upcoming'}
          {session.status === 'completed' && 'Completed'}
        </span>
      </div>

      <div className="mb-4 space-y-2">
        <div className="flex items-center gap-2 text-sm text-slate-700">
          <Clock className="h-4 w-4" />
          <span>
            {startTime.toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
            })}{' '}
            -{' '}
            {endTime.toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-700">
          <MapPin className="h-4 w-4" />
          <span>{session.location}</span>
        </div>
        <div className="text-xs text-slate-600">
          <span className="font-mono">{session.classCode}</span>
        </div>
      </div>

      <Button
        onClick={onMarkAttendance}
        variant="default"
        className="w-full"
        disabled={session.status === 'completed'}
      >
        {session.status === 'completed' ? 'Session Ended' : 'Mark Attendance'}
      </Button>
    </div>
  );
};
