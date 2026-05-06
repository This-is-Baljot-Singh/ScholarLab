import { Suspense, lazy } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowUpRight,
  CalendarClock,
  ClipboardCheck,
  Clock3,
  Loader2,
  ShieldAlert,
  Sparkles,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import {
  AuditQueuePanel,
  CurriculumVerificationQueue,
  LectureAudioUpload,
  ActiveClassroomView,
  StudentManagementTable,
} from '../components';

const LazyPredictiveAnalyticsDashboard = lazy(() =>
  import('../components/PredictiveAnalyticsDashboard').then((module) => ({
    default: module.PredictiveAnalyticsDashboard,
  }))
);

export interface FacultyDashboardPageProps {
  onNavigate?: unknown;
  currentPage?: unknown;
}

interface ActiveSessionSummary {
  id: string;
  status: string;
  title: string;
  instructor: string;
  students: number;
  startedAt: string;
}

const FALLBACK_ACTIVE_SESSIONS: ActiveSessionSummary[] = [
  {
    id: 'session-204',
    status: 'active',
    title: 'Advanced Algorithms',
    instructor: 'Dr. Sarah Chen',
    students: 24,
    startedAt: 'Today · 9:00 AM',
  },
  {
    id: 'session-218',
    status: 'active',
    title: 'Database Systems',
    instructor: 'Prof. Miguel Santos',
    students: 31,
    startedAt: 'Today · 10:15 AM',
  },
  {
    id: 'session-227',
    status: 'active',
    title: 'Applied AI Seminar',
    instructor: 'Dr. Lina Patel',
    students: 18,
    startedAt: 'Today · 11:30 AM',
  },
];

const normalizeActiveSession = (session: any, index: number): ActiveSessionSummary => ({
  id: String(session?.id ?? session?._id ?? `session-${index + 1}`),
  status: session?.status ?? 'active',
  title:
    session?.title ?? session?.lectureTitle ?? session?.lecture?.title ?? `Live session ${index + 1}`,
  instructor: session?.instructor ?? session?.facultyName ?? 'Faculty team',
  students: Number(session?.students ?? session?.attendanceCount ?? 0),
  startedAt:
    session?.startedAt ??
    session?.startTime ??
    session?.lecture?.startTime ??
    'In progress',
});

const getStatusTone = (status: string) => {
  if (status.toLowerCase() === 'active') {
    return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  }

  return 'bg-slate-100 text-slate-600 border-slate-200';
};

const FacultyMetric = ({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
}) => (
  <div className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex items-center gap-3">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      </div>
    </div>
  </div>
);

const AnalyticsChunkFallback = () => (
  <div className="flex h-[28rem] items-center justify-center rounded-[1.75rem] border border-dashed border-slate-200 bg-white text-slate-500 shadow-sm">
    <div className="flex items-center gap-3">
      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
      <span className="text-sm font-medium">Loading analytics…</span>
    </div>
  </div>
);

export const FacultyDashboardPage = (_props: FacultyDashboardPageProps) => {
  const user = useAuthStore((state) => state.user);

  const { data: activeSessionsData, isLoading: isLoadingSessions } = useQuery<ActiveSessionSummary[]>({
    queryKey: ['faculty-active-sessions'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/analytics/sessions/active');
        const sessions = Array.isArray(response.data) ? response.data : [];

        if (sessions.length === 0) {
          return FALLBACK_ACTIVE_SESSIONS;
        }

        return sessions.map(normalizeActiveSession);
      } catch {
        return FALLBACK_ACTIVE_SESSIONS;
      }
    },
    staleTime: 60_000,
  });

  const { data: auditQueue = [] } = useQuery({
    queryKey: ['audit-queue'],
    queryFn: async () => {
      const response = await apiClient.get('/attendance/audit-queue');
      return response.data;
    },
    staleTime: 30_000,
  });

  const { data: curriculumQueue = [] } = useQuery({
    queryKey: ['curriculum-verification-queue'],
    queryFn: async () => {
      const response = await apiClient.get('/curriculum/verification-queue');
      return response.data;
    },
    staleTime: 30_000,
  });

  const activeSessions = activeSessionsData ?? FALLBACK_ACTIVE_SESSIONS;
  const sessionId = activeSessions[0]?.id ?? null;

  return (
    <div className="space-y-8 pb-4">
      <section
        id="overview"
        className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm"
      >
        <div className="grid gap-0 lg:grid-cols-[1.3fr_0.85fr]">
          <div className="bg-gradient-to-br from-indigo-600 via-indigo-600 to-slate-900 p-8 text-white sm:p-10">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center rounded-full bg-white/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-white/80">
                Faculty Workspace
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white/90">
                <Sparkles className="h-3.5 w-3.5" />
                Predictive analytics ready
              </span>
            </div>

            <div className="mt-8 max-w-2xl space-y-5">
              <p className="text-sm font-medium text-white/70">Welcome back, {user?.name ?? 'Faculty'}</p>
              <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
                Keep live instruction, verification, and risk tracking in one place.
              </h1>
              <p className="max-w-xl text-sm leading-7 text-white/75 sm:text-base">
                This workspace surfaces active sessions, the pending curriculum verification queue,
                and the predictive analytics dashboard used to monitor student risk in real time.
              </p>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <FacultyMetric label="Active sessions" value={String(activeSessions.length)} icon={CalendarClock} />
              <FacultyMetric label="Verification" value={String(auditQueue.length + curriculumQueue.length)} icon={ClipboardCheck} />
              <FacultyMetric label="Analytics feed" value="Live" icon={ShieldAlert} />
            </div>
          </div>

          <div className="grid gap-4 bg-slate-50 p-6 sm:grid-cols-2 lg:grid-cols-1 lg:p-8">
            <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Current workload</p>
              <div className="mt-4 flex items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-slate-500">Sessions in progress</p>
                  <p className="mt-2 text-3xl font-semibold text-slate-900">{activeSessions.length}</p>
                </div>
                <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  Stable
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {activeSessions.slice(0, 2).map((session) => (
                  <div key={session.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{session.title}</p>
                        <p className="mt-1 text-xs text-slate-500">{session.instructor}</p>
                      </div>
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${getStatusTone(session.status)}`}>
                        {session.status}
                      </span>
                    </div>
                    <div className="mt-3 flex items-center justify-between gap-3 text-sm text-slate-500">
                      <span className="inline-flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        {session.students} students
                      </span>
                      <span>{session.startedAt}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Latest analytics</p>
              <div className="mt-4 rounded-2xl bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">Predictive analytics dashboard</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  The live model is pinned below. Use the current session to keep SHAP explanations
                  and attendance risk synced to the class you are teaching.
                </p>
              </div>

              <button
                type="button"
                className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600 transition hover:text-indigo-700"
              >
                Jump to analytics
                <ArrowUpRight className="h-4 w-4" />
              </button>

              <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">Pending reviews</p>
                <div className="mt-2 flex gap-4">
                  <div className="flex-1">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-tighter">Attendance</p>
                    <p className="text-lg font-bold text-slate-800">{auditQueue.length}</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-tighter">Curriculum</p>
                    <p className="text-lg font-bold text-slate-800">{curriculumQueue.length}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="active-sessions" className="space-y-4 scroll-mt-28">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              Active sessions
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">
              Live teaching sessions at a glance
            </h2>
          </div>
          {isLoadingSessions ? (
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-500">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
              Syncing sessions
            </span>
          ) : (
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-500">
              <Clock3 className="h-3.5 w-3.5 text-indigo-600" />
              {activeSessions.length} live
            </span>
          )}
        </div>

        {/* Active Classroom View */}
        <div className="mb-6">
          <ActiveClassroomView sessionId={sessionId || undefined} showDetails={true} />
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              {activeSessions.map((session) => (
                <article
                  key={session.id}
                  className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-600">
                        {session.status}
                      </p>
                      <h3 className="mt-2 text-lg font-semibold text-slate-900">{session.title}</h3>
                    </div>
                    <div className="rounded-2xl bg-indigo-50 p-3 text-indigo-600">
                      <CalendarClock className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="mt-5 space-y-3 text-sm text-slate-600">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-slate-400" />
                      <span>{session.students} students engaged</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock3 className="h-4 w-4 text-slate-400" />
                      <span>{session.startedAt}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600 transition hover:text-indigo-700"
                  >
                    Open session
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                </article>
              ))}
            </div>
          </div>
          <div className="lg:col-span-1">
            <LectureAudioUpload 
              sessionId={sessionId || 'unknown'} 
              courseId="CS101" // In a real app this would come from the session context
            />
          </div>
        </div>
      </section>

      <section id="verification-queue" className="space-y-4 scroll-mt-28">
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
      </section>

      <section id="student-management" className="space-y-4 scroll-mt-28">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Student Administration
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">
            Monitor enrollment, attendance, and risk
          </h2>
        </div>

        <StudentManagementTable courseId="CS101" maxRows={15} />
      </section>

      <section id="analytics-dashboard" className="space-y-4 scroll-mt-28">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Predictive analytics dashboard
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">
            ML-powered student risk assessment and explanations
          </h2>
        </div>

        <Suspense fallback={<AnalyticsChunkFallback />}>
          <LazyPredictiveAnalyticsDashboard sessionId={sessionId} />
        </Suspense>
      </section>
    </div>
  );
};
