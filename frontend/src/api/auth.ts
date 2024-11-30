import type { LoginCredentials, RegisterCredentials, AuthResponse, User } from '@/types/auth';
import { API_BASE_URL } from '@/lib/utils';

const AUTH_ENDPOINTS = {
  login: `${API_BASE_URL}/auth/login`,
  register: `${API_BASE_URL}/auth/register`,
  me: `${API_BASE_URL}/users/me`,
};

export const authApi = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    formData.append('grant_type', 'password');

    const response = await fetch(AUTH_ENDPOINTS.login, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to login');
    }

    return response.json();
  },

  async register(credentials: RegisterCredentials): Promise<User> {
    const response = await fetch(AUTH_ENDPOINTS.register, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to register');
    }

    return response.json();
  },

  async getCurrentUser(token: string): Promise<User> {
    const response = await fetch(AUTH_ENDPOINTS.me, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get user profile');
    }

    return response.json();
  },
};