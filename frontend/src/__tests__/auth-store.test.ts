// src/__tests__/auth-store.test.ts
import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '@/store/auth';
import { authApi } from '@/api/auth';

// Mock the authApi module
jest.mock('@/api/auth');

const mockedAuthApi = authApi as jest.Mocked<typeof authApi>;

describe('Auth Store', () => {
  beforeEach(() => {
    // Clear all instances and calls to constructor and all methods:
    jest.resetAllMocks();

    // Mock the login function
    mockedAuthApi.login.mockResolvedValue({
      access_token: 'fake-token',
      token_type: 'Bearer',
    });

    // Mock the getCurrentUser function
    mockedAuthApi.getCurrentUser.mockResolvedValue({
      id: '1',
      username: 'testuser',
      email: 'testuser@example.com', // Added email field
    });

    // Mock the register function
    mockedAuthApi.register.mockResolvedValue({
      id: '1',
      username: 'testuser',
      email: 'testuser@example.com', // Added email field
    });
  });

  it('should initialize with default values', () => {
    const { result } = renderHook(() => useAuthStore());
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBeFalsy();
    expect(result.current.isLoading).toBeFalsy();
    expect(result.current.error).toBeNull();
  });

  it('should handle login successfully', async () => {
    const { result } = renderHook(() => useAuthStore());

    await act(async () => {
      await result.current.login({
        username: 'testuser',
        password: 'Test123!',
      });
    });

    expect(mockedAuthApi.login).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'Test123!',
    });

    expect(mockedAuthApi.getCurrentUser).toHaveBeenCalledWith('fake-token');

    expect(result.current.isAuthenticated).toBeTruthy();
    expect(result.current.token).toBe('fake-token');
    expect(result.current.user).toEqual({
      id: '1',
      username: 'testuser',
      email: 'testuser@example.com', // Ensure email is included
    });
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBeFalsy();
  });

  it('should handle login failure', async () => {
    // Mock login to reject with an error
    mockedAuthApi.login.mockRejectedValue(new Error('Invalid credentials'));

    const { result } = renderHook(() => useAuthStore());

    await act(async () => {
      await result.current.login({
        username: 'wronguser',
        password: 'wrongpassword',
      });
    });

    expect(result.current.isAuthenticated).toBeFalsy();
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
    expect(result.current.error).toBe('Invalid credentials');
    expect(result.current.isLoading).toBeFalsy();
  });

  it('should handle logout', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBeFalsy();
    expect(result.current.error).toBeNull();
  });

  // Add more tests as needed, e.g., for registration
});
