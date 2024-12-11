export interface User{
  id?: string;  // Adding this line
  username:string;
  email:string;
  full_name?: string;
}

export interface LoginCredentials{
  username: string;
  password: string;
}

export interface RegisterCredentials{
  username: string;
  email: string;
  password: string;
  full_name?:string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface AuthStore extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}