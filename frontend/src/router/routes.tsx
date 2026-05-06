import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Link } from 'react-router-dom';
import { ProtectedRoute } from '@/features/auth/components/ProtectedRoute';
import { LoginPage } from '@/features/auth/pages';
import { MainLayout, AuthLayout } from '@/shared/layouts';
import { USER_ROLES } from '@/constants/auth';
import { useAuthStore } from '@/store/authStore';
import { ROLE_BASE_PATHS, getRolePath } from '@/shared/roleShell';
import { Loader2, ShieldAlert } from 'lucide-react';

const LazyStudentDashboardPage = lazy(() =>
  import('@/features/attendance/pages/StudentDashboardPage').then((module) => ({
    default: module.StudentDashboardPage,
  }))
);

const LazyUpcomingSessionsPage = lazy(() =>
  import('@/features/attendance/pages/UpcomingSessionsPage').then((module) => ({
    default: module.UpcomingSessionsPage,
  }))
);

const LazyStudentRiskPosturePage = lazy(() =>
  import('@/features/attendance/pages/StudentRiskPosturePage').then((module) => ({
    default: module.StudentRiskPosturePage,
  }))
);

const LazyUnlockedResourcesPage = lazy(() =>
  import('@/features/attendance/pages/UnlockedResourcesPage').then((module) => ({
    default: module.UnlockedResourcesPage,
  }))
);

const LazyFacultyLayout = lazy(() =>
  import('@/features/faculty/pages').then((module) => ({
    default: module.FacultyLayout,
  }))
);

const LazyFacultyOverview = lazy(() =>
  import('@/features/faculty/pages').then((module) => ({
    default: module.FacultyOverview,
  }))
);

const LazyActiveSessionsPage = lazy(() =>
  import('@/features/faculty/pages').then((module) => ({
    default: module.ActiveSessionsPage,
  }))
);

const LazyVerificationQueuePage = lazy(() =>
  import('@/features/faculty/pages').then((module) => ({
    default: module.VerificationQueuePage,
  }))
);

const LazyPredictiveAnalyticsPage = lazy(() =>
  import('@/features/faculty/pages').then((module) => ({
    default: module.PredictiveAnalyticsPage,
  }))
);

const LazyStudentProfilePage = lazy(() =>
  import('@/features/faculty/pages').then((module) => ({
    default: module.StudentProfilePage,
  }))
);

const LazyAdminDashboardPage = lazy(() =>
  import('@/features/admin/pages/AdminDashboardPage').then((module) => ({
    default: module.AdminDashboardPage,
  }))
);

import { GeofencesPage } from '@/features/admin/pages/GeofencesPage';
import { UserManagementPage } from '@/features/admin/pages/UserManagementPage';
import { AuditLogsPage } from '@/features/admin/pages/AuditLogsPage';

const WorkspaceChunkFallback = () => (
  <div className="flex min-h-[60vh] items-center justify-center rounded-[2rem] border border-dashed border-slate-200 bg-white/80 text-slate-500">
    <div className="flex items-center gap-3">
      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
      <span className="text-sm font-medium">Loading workspace…</span>
    </div>
  </div>
);

// Standard workspace shell for Student and Admin
const WorkspaceShell = ({ role }: { role: (typeof USER_ROLES)[keyof typeof USER_ROLES] }) => (
  <ProtectedRoute requiredRoles={[role]}>
    <Suspense fallback={<WorkspaceChunkFallback />}>
      <MainLayout />
    </Suspense>
  </ProtectedRoute>
);

const Unauthorized = () => (
  <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
    <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-xl shadow-slate-900/5">
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50 text-red-600">
        <ShieldAlert className="h-7 w-7" />
      </div>
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Access restricted</p>
      <h1 className="mt-4 text-3xl font-semibold text-slate-900">
        You do not have permission to open this workspace.
      </h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        ScholarLab only exposes Student, Faculty, and Admin surfaces. Return to your assigned
        dashboard to continue.
      </p>
      <Link
        to="/"
        className="mt-6 inline-flex items-center justify-center rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700"
      >
        Return to dashboard
      </Link>
    </div>
  </div>
);

const RootDispatcher = () => {
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getRolePath(user.role)} replace />;
};

export const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <AuthLayout>
        <LoginPage />
      </AuthLayout>
    ),
  },
  {
    path: '/',
    element: <RootDispatcher />,
  },
  {
    path: ROLE_BASE_PATHS.student,
    element: <WorkspaceShell role={USER_ROLES.STUDENT} />,
    children: [
      {
        index: true,
        element: <Navigate to="overview" replace />,
      },
      {
        path: 'overview',
        element: <LazyStudentDashboardPage />,
      },
      {
        path: 'upcoming-sessions',
        element: <LazyUpcomingSessionsPage />,
      },
      {
        path: 'risk-score',
        element: <LazyStudentRiskPosturePage />,
      },
      {
        path: 'resources',
        element: <LazyUnlockedResourcesPage />,
      },
    ],
  },
  {
    path: ROLE_BASE_PATHS.faculty,
    element: (
      <ProtectedRoute requiredRoles={[USER_ROLES.FACULTY]}>
        <Suspense fallback={<WorkspaceChunkFallback />}>
          <LazyFacultyLayout />
        </Suspense>
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="overview" replace />,
      },
      {
        path: 'overview',
        element: <LazyFacultyOverview />,
      },
      {
        path: 'active-sessions',
        element: <LazyActiveSessionsPage />,
      },
      {
        path: 'verification-queue',
        element: <LazyVerificationQueuePage />,
      },
      {
        path: 'analytics-dashboard',
        element: <LazyPredictiveAnalyticsPage />,
      },
      {
        path: 'students/:student_id',
        element: <LazyStudentProfilePage />,
      },
    ],
  },
  {
    path: ROLE_BASE_PATHS.admin,
    element: <WorkspaceShell role={USER_ROLES.ADMIN} />,
    children: [
      {
        index: true,
        element: <Navigate to="overview" replace />,
      },
      {
        path: 'overview',
        element: <LazyAdminDashboardPage />,
      },
      {
        path: 'geofences',
        element: (
          <Suspense fallback={<WorkspaceChunkFallback />}>
            <GeofencesPage />
          </Suspense>
        ),
      },
      {
        path: 'audit-logs',
        element: (
          <Suspense fallback={<WorkspaceChunkFallback />}>
            <AuditLogsPage />
          </Suspense>
        ),
      },
      {
        path: 'user-management',
        element: (
          <Suspense fallback={<WorkspaceChunkFallback />}>
            <UserManagementPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: '/unauthorized',
    element: <Unauthorized />,
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
