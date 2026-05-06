import { useMemo, useState } from 'react';
import { useLocation, Outlet } from 'react-router-dom';
import type { UserRole } from '@/types/auth';
import { useAuthStore } from '@/store/authStore';
import { ROLE_SHELL_CONFIG } from '@/shared/roleShell';
import { Sidebar } from './Sidebar';
import { TopAppBar } from './TopAppBar';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout = () => {
  const location = useLocation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const user = useAuthStore((state) => state.user);

  const role: UserRole = user?.role ?? 'student';
  const shellConfig = ROLE_SHELL_CONFIG[role];

  const activeNavItem = useMemo(() => {
    return (
      shellConfig.navItems.find((item) => item.path === location.pathname) ??
      shellConfig.navItems[0]
    );
  }, [location.pathname, shellConfig.navItems]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-24 top-0 h-72 w-72 rounded-full bg-indigo-100/70 blur-3xl" />
        <div className="absolute left-[-5rem] top-40 h-96 w-96 rounded-full bg-slate-200/70 blur-3xl" />
      </div>

      <div className="relative z-10 flex min-h-screen">
        <Sidebar />

        {mobileSidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-sm md:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
        )}

        {mobileSidebarOpen && (
          <Sidebar 
            isMobile 
            onCloseMobile={() => setMobileSidebarOpen(false)} 
          />
        )}

        <div className="flex min-h-screen flex-1 flex-col">
          <TopAppBar
            onMenuClick={() => setMobileSidebarOpen(true)}
            activeItemLabel={activeNavItem.label}
            activeItemDescription={activeNavItem.description}
          />

          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export const AuthLayout = ({ children }: MainLayoutProps) => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 via-indigo-50 to-slate-100 px-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
};
