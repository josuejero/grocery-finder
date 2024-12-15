// frontend/src/store/auth.ts

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthStore, RegisterCredentials, LoginCredentials } from "@/types/auth";
import { authApi } from "@/api/auth";

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
          const token = authResponse.access_token;
          
          // Store token in both localStorage and state
          localStorage.setItem("auth-token", token);
          console.log('🔑 Token stored:', token.substring(0, 20) + '...');
          
          // Get user data before setting auth state
          const user = await authApi.getCurrentUser(token);
          
          set({
            token,
            user,
            isAuthenticated: true,
            error: null,
            isLoading: false
          });
        } catch (error: unknown) {
          console.error('❌ Login error:', error);
          localStorage.removeItem("auth-token");
          set({
            user: null,
            token: null, 
            isAuthenticated: false,
            error: error instanceof Error ? error.message : "Login failed",
            isLoading: false
          });
          throw error;
        }
      },

      register: async (credentials: RegisterCredentials) => {
        set({ isLoading: true, error: null });
        try {
          await authApi.register(credentials);
          set({ isLoading: false });
        } catch (error: unknown) {
          set({
            error: error instanceof Error ? error.message : "Failed to register",
            isLoading: false
          });
          throw error;
        }
      },

      logout: () => {
        localStorage.removeItem("auth-token");
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null
        });
      },

      clearError: () => set({ error: null })
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);