import React from 'react';
import { Menu, LogOut } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useLogout } from '@/features/auth/hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { getRoleLabel, ROLE_SHELL_CONFIG } from '@/shared/roleShell';
import type { UserRole } from '@/types/auth';

interface TopAppBarProps {
  onMenuClick: () => void;
  activeItemLabel: string;
  activeItemDescription: string;
}

export const TopAppBar: React.FC<TopAppBarProps> = ({
  onMenuClick,
  activeItemLabel,
  activeItemDescription,
}) => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useLogout();

  const role: UserRole = user?.role ?? 'student';

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

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 md:hidden"
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              ScholarLab Workspace
            </p>
            <h1 className="mt-1 text-lg font-semibold text-slate-900">
              {activeItemLabel}
            </h1>
            <p className="text-sm text-slate-500">{activeItemDescription}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 sm:inline-flex">
            {getRoleLabel(role)}
          </span>
          <div className="flex max-w-[16rem] items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-sm font-semibold text-white">
              {initials || 'SL'}
            </div>
            <div className="hidden min-w-0 sm:block">
              <p className="truncate text-sm font-semibold text-slate-900">{user?.name ?? 'ScholarLab user'}</p>
              <p className="truncate text-xs text-slate-500">{user?.email ?? 'No email available'}</p>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
