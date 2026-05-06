import {
  Activity,
  BarChart3,
  BookOpen,
  CalendarClock,
  ClipboardCheck,
  LayoutDashboard,
  Map as MapIcon,
  ScrollText,
  ShieldAlert,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ROLE_LABELS } from '@/constants/auth';
import type { UserRole } from '@/types/auth';

export const ROLE_BASE_PATHS: Record<UserRole, string> = {
  student: '/student',
  faculty: '/faculty',
  admin: '/admin',
};

export const getRolePath = (role?: UserRole | null, sectionId = 'overview') => {
  switch (role) {
    case 'student':
      return `${ROLE_BASE_PATHS.student}/${sectionId}`;
    case 'faculty':
      return `${ROLE_BASE_PATHS.faculty}/${sectionId}`;
    case 'admin':
      return `${ROLE_BASE_PATHS.admin}/${sectionId}`;
    default:
      return '/unauthorized';
  }
};

export const getRoleLabel = (role?: UserRole | null) => {
  switch (role) {
    case 'student':
      return ROLE_LABELS.student;
    case 'faculty':
      return ROLE_LABELS.faculty;
    case 'admin':
      return ROLE_LABELS.admin;
    default:
      return 'Guest';
  }
};

export interface ShellNavItem {
  label: string;
  description: string;
  path: string;
  icon: LucideIcon;
}

export interface ShellRoleConfig {
  title: string;
  subtitle: string;
  navItems: ShellNavItem[];
}

export const ROLE_SHELL_CONFIG: Record<UserRole, ShellRoleConfig> = {
  student: {
    title: 'Student Dashboard',
    subtitle: 'Track upcoming sessions, your current risk score, and unlocked curriculum resources.',
    navItems: [
      {
        label: 'Overview',
        description: 'Today\'s learning snapshot and status.',
        path: getRolePath('student', 'overview'),
        icon: LayoutDashboard,
      },
      {
        label: 'Upcoming Sessions',
        description: 'See what is next on your schedule.',
        path: getRolePath('student', 'upcoming-sessions'),
        icon: CalendarClock,
      },
      {
        label: 'Risk Score',
        description: 'Review your current risk posture.',
        path: getRolePath('student', 'risk-score'),
        icon: ShieldAlert,
      },
      {
        label: 'Unlocked Resources',
        description: 'Open the latest curriculum material.',
        path: getRolePath('student', 'resources'),
        icon: BookOpen,
      },
    ],
  },
  faculty: {
    title: 'Faculty Workspace',
    subtitle: 'Monitor live sessions, resolve curriculum verification, and inspect predictive analytics.',
    navItems: [
      {
        label: 'Overview',
        description: 'Command-center summary for the day.',
        path: getRolePath('faculty', 'overview'),
        icon: LayoutDashboard,
      },
      {
        label: 'Active Sessions',
        description: 'Track the live teaching surface.',
        path: getRolePath('faculty', 'active-sessions'),
        icon: CalendarClock,
      },
      {
        label: 'Verification Queue',
        description: 'Resolve pending curriculum checks.',
        path: getRolePath('faculty', 'verification-queue'),
        icon: ClipboardCheck,
      },
      {
        label: 'Predictive Analytics',
        description: 'Inspect the live risk model and SHAP insights.',
        path: getRolePath('faculty', 'analytics-dashboard'),
        icon: BarChart3,
      },
    ],
  },
  admin: {
    title: 'Admin Control Center',
    subtitle: 'Monitor system health, audit activity, and manage users from one secured surface.',
    navItems: [
      {
        label: 'Overview',
        description: 'Operational snapshot and live signals.',
        path: getRolePath('admin', 'overview'),
        icon: LayoutDashboard,
      },
      {
        label: 'Geofences',
        description: 'Manage campus spatial boundaries.',
        path: getRolePath('admin', 'geofences'),
        icon: MapIcon,
      },
      {
        label: 'User Directory',
        description: 'Manage access control and identity.',
        path: getRolePath('admin', 'user-management'),
        icon: Users,
      },
      {
        label: 'Audit Logs',
        description: 'Review privileged security events.',
        path: getRolePath('admin', 'audit-logs'),
        icon: ScrollText,
      },
    ],
  },
};