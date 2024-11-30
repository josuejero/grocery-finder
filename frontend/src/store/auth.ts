import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthStore, LoginCredentials, RegisterCredentials } from '@/types/auth';
import { authApi } from '@/api/auth';

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });
        try {
          const authResponse = await authApi.login(credentials);
          const user = await authApi.getCurrentUser(authResponse.access_token);
          set({
            user,
            token: authResponse.access_token,
            isAuthenticated: true,
            error: null,
          });
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to login' });
        } finally {
          set({ isLoading: false });
        }
      },

      register: async (credentials: RegisterCredentials) => {
        set({ isLoading: true, error: null });
        try {
          await authApi.register(credentials);
          // After registration, login the user
          await useAuthStore.getState().login({
            username: credentials.username,
            password: credentials.password,
          });
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to register' });
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);