import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, AuthTokens, AuthState } from '@/types/auth';

interface AuthStore extends AuthState {
  setUser: (user: User | null) => void;
  setTokens: (tokens: AuthTokens | null) => void;
  setIsAuthenticated: (isAuthenticated: boolean) => void;
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  login: (user: User, tokens: AuthTokens) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  refreshAccessToken: (newAccessToken: string) => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      tokens: null,

      setUser: (user) => set({ user }),

      setTokens: (tokens) => set({ tokens }),

      setIsAuthenticated: (isAuthenticated) => set({ isAuthenticated }),

      setIsLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error }),

      login: (user, tokens) =>
        set({
          user,
          tokens,
          isAuthenticated: true,
          error: null,
        }),

      logout: () =>
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          error: null,
        }),

      updateUser: (updatedUser) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updatedUser } : null,
        })),

      refreshAccessToken: (newAccessToken) =>
        set((state) => ({
          tokens: state.tokens
            ? {
                ...state.tokens,
                accessToken: newAccessToken,
              }
            : null,
        })),
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
