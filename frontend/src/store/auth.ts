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
          
          // Store token in both localStorage and state
          const token = authResponse.access_token;
          localStorage.setItem("auth-token", token);
          console.log('🔑 Token stored:', token.substring(0, 20) + '...');
          
          set({
            token,
            isAuthenticated: true,
            error: null,
          });
          
          const user = await authApi.getCurrentUser(token);
          set({ user });
        } catch (error: unknown) { // Changed from 'any' to 'unknown'
          console.error('❌ Login error:', error);
          localStorage.removeItem("auth-token"); // Clean up on error
          set({
            error: error instanceof Error ? error.message : "Login failed",
          });
        } finally {
          set({ isLoading: false });
        }
      },


      register: async (credentials: RegisterCredentials) => {
        set({ isLoading: true, error: null });
        try {
          await authApi.register(credentials);
        } catch (error: unknown) {
          set({
            error: error instanceof Error ? error.message : "Failed to register",
          });
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        localStorage.removeItem("auth-token");
        set({ user: null, token: null, isAuthenticated: false });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
