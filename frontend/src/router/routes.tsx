
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '@/features/auth/components/ProtectedRoute';
import { LoginPage } from '@/features/auth/pages';
import { StudentDashboardPage } from '@/features/attendance/pages';
import { FacultyPortal } from '@/features/faculty/FacultyPortal';
import { MainLayout, AuthLayout } from '@/shared/layouts';
import { USER_ROLES } from '@/constants/auth';
import { useAuthStore } from '@/store/authStore';

// Placeholder pages - to be replaced with actual components
const AdminPanel = () => (
  <div className="p-8 text-center text-xl font-bold">Admin Panel</div>
);
const Unauthorized = () => (
  <div className="flex h-screen items-center justify-center bg-slate-50">
    <div className="text-center">
      <h1 className="text-4xl font-bold text-red-600 mb-2">403</h1>
      <p className="text-slate-600">You do not have permission to access this area.</p>
    </div>
  </div>
);

/**
 * Smart Dispatcher: Evaluates the user's role at the root level
 * and redirects them to their designated workspace.
 */
const RootDispatcher = () => {
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === USER_ROLES.FACULTY || user.role === USER_ROLES.ADMIN) {
    return <Navigate to="/faculty" replace />;
  }

  // Default to student view for students
  return (
    <MainLayout>
      <StudentDashboardPage />
    </MainLayout>
  );
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
    path: '/attendance',
    element: (
      <MainLayout>
        {/* Strictly STUDENT only */}
        <ProtectedRoute requiredRoles={[USER_ROLES.STUDENT]}>
          <StudentDashboardPage />
        </ProtectedRoute>
      </MainLayout>
    ),
  },
  {
    path: '/curriculum',
    element: (
      <MainLayout>
        {/* Strictly STUDENT only */}
        <ProtectedRoute requiredRoles={[USER_ROLES.STUDENT]}>
          <StudentDashboardPage />
        </ProtectedRoute>
      </MainLayout>
    ),
  },
  {
    path: '/faculty',
    element: (
      // FacultyPortal likely has its own layout shell built-in
      <ProtectedRoute requiredRoles={[USER_ROLES.FACULTY, USER_ROLES.ADMIN]}>
        <FacultyPortal />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin',
    element: (
      <MainLayout>
        <ProtectedRoute requiredRoles={[USER_ROLES.ADMIN]}>
          <AdminPanel />
        </ProtectedRoute>
      </MainLayout>
    ),
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
