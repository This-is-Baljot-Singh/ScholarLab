import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LogOut, X } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useLogout } from '@/features/auth/hooks/useAuth';
import { getRoleLabel, ROLE_SHELL_CONFIG } from '@/shared/roleShell';
import type { UserRole } from '@/types/auth';

interface SidebarProps {
  onCloseMobile?: () => void;
  isMobile?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ onCloseMobile, isMobile }) => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useLogout();

  const role: UserRole = user?.role ?? 'student';
  const shellConfig = ROLE_SHELL_CONFIG[role];

  const initials = (user?.name ?? 'ScholarLab')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navContent = (
    <div className="flex h-full flex-col bg-white/95 backdrop-blur">
      <div className="flex items-start justify-between border-b border-slate-200/80 px-5 py-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-indigo-600">
            ScholarLab
          </p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">{shellConfig.title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">{shellConfig.subtitle}</p>
        </div>
        {isMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-4 py-5">
        <div className="rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-600 to-slate-900 p-4 text-white shadow-lg shadow-indigo-950/10">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/70">
            Signed in as
          </p>
          <div className="mt-4 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 text-sm font-semibold text-white">
              {initials || 'SL'}
            </div>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold">{user?.name ?? 'ScholarLab user'}</p>
              <p className="truncate text-sm text-white/70">{user?.email ?? 'No email available'}</p>
            </div>
          </div>
          <div className="mt-4 inline-flex items-center rounded-full bg-white/15 px-3 py-1 text-xs font-semibold text-white">
            {getRoleLabel(role)}
          </div>
        </div>

        <nav aria-label="Primary" className="space-y-2">
          {shellConfig.navItems.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `group flex items-start gap-3 rounded-2xl border px-4 py-3 transition-all duration-200 ${
                    isActive
                      ? 'border-indigo-200 bg-indigo-50 text-indigo-900 shadow-sm'
                      : 'border-transparent bg-white text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`mt-0.5 inline-flex h-10 w-10 flex-none items-center justify-center rounded-2xl transition-colors ${
                        isActive ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500 group-hover:bg-white'
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold">{item.label}</span>
                      <span className="mt-1 block text-xs leading-5 text-current/70 opacity-70">
                        {item.description}
                      </span>
                    </span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="border-t border-slate-200/80 p-4">
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </div>
  );

  if (isMobile) {
    return <aside className="fixed inset-y-0 left-0 z-50 w-80 border-r border-slate-200/80 shadow-2xl shadow-slate-900/10 transition-transform duration-300">
      {navContent}
    </aside>;
  }

  return (
    <aside className="hidden w-80 flex-shrink-0 border-r border-slate-200/80 md:flex md:flex-col">
      {navContent}
    </aside>
  );
};
