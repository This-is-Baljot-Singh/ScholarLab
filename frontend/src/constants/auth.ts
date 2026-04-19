export const USER_ROLES = {
  STUDENT: 'student',
  FACULTY: 'faculty',
  ADMIN: 'admin',
} as const;

export const ROLE_LABELS: Record<string, string> = {
  student: 'Student',
  faculty: 'Faculty',
  admin: 'Administrator',
};

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const ACCESS_TOKEN_KEY = 'scholarlab_access_token';
export const REFRESH_TOKEN_KEY = 'scholarlab_refresh_token';
export const USER_KEY = 'scholarlab_user';

export const TOKEN_REFRESH_BUFFER = 5 * 60 * 1000; // Refresh 5 minutes before expiry
