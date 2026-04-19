import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, User } from 'lucide-react';
import { useAuthUser, useLogout, useUserRole } from '@/features/auth/hooks/useAuth';
import { USER_ROLES } from '@/constants/auth';

export const TopAppBar: React.FC = () => {
  const user = useAuthUser();
  const logout = useLogout();
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="text-2xl font-bold text-indigo-600">ScholarLab</div>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="relative">
              <button
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100">
                  <User className="w-4 h-4 text-indigo-600" />
                </div>
                <span>{user.name}</span>
              </button>

              {isProfileMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                  <div className="px-4 py-2 text-xs text-slate-500 border-b border-slate-200">
                    {user.email}
                  </div>
                  <button
                    onClick={() => {
                      logout();
                      setIsProfileMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Logout
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

interface NavLink {
  label: string;
  path: string;
  icon?: React.ReactNode;
  roles: (typeof USER_ROLES)[keyof typeof USER_ROLES][];
}

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = true, onClose }) => {
  const location = useLocation();
  const userRole = useUserRole();

  const navLinks: NavLink[] = [
    {
      label: 'Dashboard',
      path: '/',
      roles: [USER_ROLES.STUDENT, USER_ROLES.FACULTY, USER_ROLES.ADMIN],
    },
    {
      label: 'Attendance',
      path: '/attendance',
      roles: [USER_ROLES.STUDENT, USER_ROLES.FACULTY, USER_ROLES.ADMIN],
    },
    {
      label: 'Curriculum',
      path: '/curriculum',
      roles: [USER_ROLES.STUDENT, USER_ROLES.FACULTY, USER_ROLES.ADMIN],
    },
    {
      label: 'Admin Panel',
      path: '/admin',
      roles: [USER_ROLES.ADMIN],
    },
  ];

  const filteredLinks = navLinks.filter(
    (link) => !userRole || link.roles.includes(userRole)
  );

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed left-0 top-16 z-40 flex h-[calc(100vh-64px)] w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-200 md:relative md:top-0 md:translate-x-0 md:h-[calc(100vh-64px)] ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <nav className="flex-1 overflow-y-auto px-4 py-6">
          <ul className="space-y-2">
            {filteredLinks.map((link) => (
              <li key={link.path}>
                <Link
                  to={link.path}
                  onClick={() => onClose?.()}
                  className={`flex items-center gap-3 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    location.pathname === link.path
                      ? 'bg-indigo-50 text-indigo-700 border-l-2 border-indigo-600'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {link.icon}
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
    </>
  );
};
