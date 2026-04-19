import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { useAuthStore } from '@/store/authStore';
import type { LoginCredentials, AuthResponse } from '@/types/auth';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/constants/auth';

export const useLogin = () => {
  const setUser = useAuthStore((state) => state.setUser);
  const setTokens = useAuthStore((state) => state.setTokens);
  const setIsAuthenticated = useAuthStore((state) => state.setIsAuthenticated);
  const setError = useAuthStore((state) => state.setError);

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
      return response.data;
    },
    onSuccess: (data) => {
      const { user, tokens } = data;
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
      setUser(user);
      setTokens(tokens);
      setIsAuthenticated(true);
      setError(null);
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'Login failed';
      setError(message);
    },
  });
};

export const useLogout = () => {
  const logout = useAuthStore((state) => state.logout);

  return () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    logout();
  };
};

export const useAuthUser = () => {
  return useAuthStore((state) => state.user);
};

export const useIsAuthenticated = () => {
  return useAuthStore((state) => state.isAuthenticated);
};

export const useUserRole = () => {
  const user = useAuthStore((state) => state.user);
  return user?.role;
};
