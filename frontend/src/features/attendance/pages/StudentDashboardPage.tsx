import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  CalendarClock,
  Clock3,
  Loader2,
  MapPin,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  Wifi,
  WifiOff,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useAuthStore } from '@/store/authStore';
import { useStudentWebSocket } from '@/shared/hooks/useStudentWebSocket';
import { Button } from '@/shared/ui/Button';
import { ErrorBoundary, AsyncErrorBoundary } from '@/shared/components/ErrorBoundary';
import { MarkAttendanceFlow } from '../components';
import { StudentCurriculumView } from '@/features/curriculum/components/StudentCurriculumView';
import { StudentPerformanceRadar } from '@/features/analytics/components/StudentPerformanceRadar';
import type { StudentDashboard } from '@/types/student';

interface RecentUnlockedModule {
  id: string;
  course_id: string;
  title: string;
  unlocked_at: string;
  resource_uris: string[];
}

interface UpcomingSession {
  title: string;
  time: string;
  location: string;
  note: string;
}

const UPCOMING_SESSIONS: UpcomingSession[] = [
  {
    title: 'Data Structures Lab',
    time: 'Today · 2:00 PM',
    location: 'Engineering Hall 204',
    note: 'Attendance verification opens 15 minutes before class.',
  },
  {
    title: 'Applied AI Seminar',
    time: 'Wednesday · 10:30 AM',
    location: 'Learning Studio 3',
    note: 'A new curriculum unlock is queued after the session.',
  },
  {
    title: 'Database Systems',
    time: 'Friday · 1:00 PM',
    location: 'Main Lecture Theatre',
    note: 'Bring your device for the zero-trust check-in.',
  },
];

const getRiskTone = (riskScore: number) => {
  if (riskScore >= 70) {
    return {
      pill: 'bg-rose-100 text-rose-700 border-rose-200',
      meter: 'bg-rose-500',
      label: 'High',
    };
  }

  if (riskScore >= 45) {
    return {
      pill: 'bg-amber-100 text-amber-700 border-amber-200',
      meter: 'bg-amber-500',
      label: 'Moderate',
    };
  }

  return {
    pill: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    meter: 'bg-emerald-500',
    label: 'Low',
  };
};

const formatUnlockDate = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

type StudentWorkspaceData = StudentDashboard & {
  riskScore?: number;
  riskLabel?: string;
};

const RiskFactor = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{label}</p>
    <p className="mt-2 text-sm font-semibold text-slate-900">{value}</p>
  </div>
);

const SessionStat = ({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
}) => (
  <div className="rounded-3xl border border-white/10 bg-white/10 p-4">
    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/60">{label}</p>
    <p className="mt-2 text-3xl font-semibold">{value}</p>
    <div className="mt-3 flex items-center gap-2 text-sm text-white/70">
      <Icon className="h-4 w-4" />
      <span>Live workspace signal</span>
    </div>
  </div>
);

export const StudentDashboardPage = () => {
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const [isAttendanceFlowOpen, setIsAttendanceFlowOpen] = useState(false);
  const { isConnected } = useStudentWebSocket();

  const { data: dashboard } = useQuery<StudentWorkspaceData>({
    queryKey: ['student-dashboard'],
    queryFn: async () => {
      const response = await apiClient.get<StudentWorkspaceData>('/student/dashboard');
      return response.data;
    },
  });

  const { data: recentUnlocks = [], isLoading: isLoadingUnlocks } = useQuery<RecentUnlockedModule[]>({
    queryKey: ['recent-unlocks'],
    queryFn: async () => {
      const response = await apiClient.get('/student/curriculum/recent');
      return response.data;
    },
  });

  if (!user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  const riskScore = dashboard?.riskScore ?? 8;
  const riskTone = getRiskTone(riskScore);
  const activeSession = dashboard?.activeSession;

  return (
    <div className="space-y-8 pb-4">
      <ErrorBoundary>
        <section
          id="overview"
          className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm"
        >
        <div className="grid gap-0 lg:grid-cols-[1.4fr_0.9fr]">
          <div className="bg-gradient-to-br from-indigo-600 via-indigo-600 to-slate-900 p-8 text-white sm:p-10">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center rounded-full bg-white/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-white/80">
                Student Workspace
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white/90">
                {isConnected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
                {isConnected ? 'Realtime sync active' : 'Reconnecting to live feed'}
              </span>
            </div>

            <div className="mt-8 max-w-2xl space-y-5">
              <p className="text-sm font-medium text-white/70">Welcome back, {user.name}</p>
              <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
                Your learning surface is ready.
              </h1>
              <p className="max-w-xl text-sm leading-7 text-white/75 sm:text-base">
                Monitor what is coming next, keep an eye on your current risk posture, and open the
                curriculum resources that were just unlocked for you.
              </p>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <SessionStat label="Upcoming" value={String(UPCOMING_SESSIONS.length)} icon={CalendarClock} />
              <SessionStat label="Risk score" value={`${riskScore}%`} icon={ShieldAlert} />
              <SessionStat label="Unlocked" value={String(recentUnlocks.length)} icon={BookOpen} />
            </div>
          </div>

          <div className="grid gap-4 bg-slate-50 p-6 sm:grid-cols-2 lg:grid-cols-1 lg:p-8">
            <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Current risk</p>
                  <h2 className="mt-2 text-3xl font-semibold text-slate-900">{riskScore}%</h2>
                </div>
                <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${riskTone.pill}`}>
                  {riskTone.label}
                </div>
              </div>

              <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${riskTone.meter}`}
                  style={{ width: `${Math.min(riskScore, 100)}%` }}
                />
              </div>

              <p className="mt-4 text-sm leading-6 text-slate-600">
                {dashboard?.riskLabel ?? 'Estimated from recent attendance cadence and curriculum unlock activity.'}
              </p>
            </div>

            <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Next session</p>
              <div className="mt-3 flex items-start gap-3">
                <div className="mt-1 flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                  <CalendarClock className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">
                    {activeSession?.lecture?.title ?? UPCOMING_SESSIONS[0].title}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {activeSession?.lecture?.startTime
                      ? new Date(activeSession.lecture.startTime).toLocaleString(undefined, {
                          weekday: 'short',
                          hour: 'numeric',
                          minute: '2-digit',
                        })
                      : UPCOMING_SESSIONS[0].time}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {activeSession?.lecture?.location ?? UPCOMING_SESSIONS[0].location}
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">Status</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {activeSession?.attendanceMarked
                    ? 'Attendance has already been verified for the current session.'
                    : 'Verification is pending for the next scheduled session.'}
                </p>
              </div>

              {activeSession && !activeSession.attendanceMarked && (
                <Button
                  onClick={() => setIsAttendanceFlowOpen(true)}
                  className="mt-4 w-full"
                  size="lg"
                >
                  Start zero-trust check-in
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>

      <section id="upcoming-sessions" className="space-y-4 scroll-mt-28">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              Upcoming sessions
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">
              Your next classes at a glance
            </h2>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-500">
            <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
            Zero-trust ready
          </span>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {UPCOMING_SESSIONS.map((session) => (
            <article
              key={session.title}
              className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-600">
                    Scheduled
                  </p>
                  <h3 className="mt-2 text-lg font-semibold text-slate-900">{session.title}</h3>
                </div>
                <div className="rounded-2xl bg-indigo-50 p-3 text-indigo-600">
                  <CalendarClock className="h-5 w-5" />
                </div>
              </div>

              <div className="mt-5 space-y-3 text-sm text-slate-600">
                <div className="flex items-center gap-2">
                  <Clock3 className="h-4 w-4 text-slate-400" />
                  <span>{session.time}</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-slate-400" />
                  <span>{session.location}</span>
                </div>
              </div>

              <p className="mt-5 text-sm leading-6 text-slate-500">{session.note}</p>

              <button
                type="button"
                className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600 transition hover:text-indigo-700"
              >
                Review details
                <ArrowRight className="h-4 w-4" />
              </button>
            </article>
          ))}
        </div>
      </section>

      <section id="risk-score" className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] scroll-mt-28">
        <ErrorBoundary>
          <StudentPerformanceRadar mockMode={true} />
        </ErrorBoundary>

        <article className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Learning signals
          </p>
          <div className="mt-4 space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">What the score means</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                A lower risk score indicates a more stable attendance and unlock pattern. A higher
                score signals that a check-in or curriculum review may be needed soon.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">Current recommendation</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Open the next session, complete attendance verification on time, and review newly
                unlocked curriculum resources before the week closes.
              </p>
            </div>
          </div>
        </article>
      </section>

      <section id="resources" className="space-y-4 scroll-mt-28">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Unlocked curriculum resources
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">
            What became available after your latest check-ins
          </h2>
        </div>

        <ErrorBoundary>
          <AsyncErrorBoundary
            isError={false}
            error={null}
            isLoading={false}
          >
            {activeSession ? (
              <StudentCurriculumView
                sessionId={activeSession.lecture.id}
                showAllUnlocked={true}
              />
            ) : (
              <div className="flex flex-col items-center justify-center rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-6 py-14 text-center">
                <BookOpen className="h-10 w-10 text-slate-300" />
                <p className="mt-4 text-lg font-semibold text-slate-900">
                  No active session
                </p>
                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                  Select a session and complete attendance verification to view curriculum
                  resources.
                </p>
              </div>
            )}
          </AsyncErrorBoundary>
        </ErrorBoundary>
      </section>

      {activeSession && (
        <MarkAttendanceFlow
          isOpen={isAttendanceFlowOpen}
          sessionId={activeSession.lecture.id}
          courseId={activeSession.lecture.id}
          geofenceId={`geo_${activeSession.lecture.classCode}`}
          lectureTitle={activeSession.lecture.title}
          lectureLocation={activeSession.lecture.location}
          onClose={() => setIsAttendanceFlowOpen(false)}
          onSuccess={() => {
            setIsAttendanceFlowOpen(false);
            queryClient.invalidateQueries({ queryKey: ['student-dashboard'] });
            queryClient.invalidateQueries({ queryKey: ['recent-unlocks'] });
            queryClient.invalidateQueries({ queryKey: ['curriculum', 'unlocked'] });
          }}
        />
      )}
      </ErrorBoundary>
    </div>
  );
};