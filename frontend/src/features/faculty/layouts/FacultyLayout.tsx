import React, { useState, useMemo, Suspense } from 'react';
import { useLocation, Outlet } from 'react-router-dom';
import { Sidebar } from '@/shared/layouts/Sidebar';
import { TopAppBar } from '@/shared/layouts/TopAppBar';
import { ROLE_SHELL_CONFIG } from '@/shared/roleShell';
import { useAuthStore } from '@/store/authStore';
import { Loader2 } from 'lucide-react';

import { FacultyWorkspaceSkeleton } from '@/shared/ui/FacultyWorkspaceSkeleton';

export const FacultyLayout: React.FC = () => {
  const location = useLocation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const user = useAuthStore((state) => state.user);

  const role = user?.role ?? 'faculty';
  const shellConfig = ROLE_SHELL_CONFIG[role];

  const activeNavItem = useMemo(() => {
    return (
      shellConfig.navItems.find((item) => item.path === location.pathname) ??
      shellConfig.navItems[0]
    );
  }, [location.pathname, shellConfig.navItems]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900">
      {/* Background decorations */}
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
              <Suspense fallback={<FacultyWorkspaceSkeleton />}>
                <Outlet />
              </Suspense>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};
