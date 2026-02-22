/**
 * src/types/auth.ts
 *
 * Shared auth types. Using explicit types instead of `any`
 * catches mismatches at compile time rather than at runtime.
 */

export interface User {
  id:          number;
  email:       string;
  full_name:   string;
  role:        string;
  department?: string;
  is_active:   boolean;
}

export interface LoginResponse {
  access:  string;
  refresh: string;
  user?:   User;   // include if your backend returns user on login
}

export interface SignupPayload {
  email:     string;
  full_name: string;
  password:  string;
}

export interface AuthContextType {
  user:            User | null;
  isAuthenticated: boolean;
  isLoading:       boolean;
  login:    (email: string, password: string) => Promise<void>;
  signup:   (payload: SignupPayload)           => Promise<void>;
  logout:   ()                                 => void;
  forgotPassword: (email: string)              => Promise<void>;
  resetPassword:  (uid: string, token: string, newPassword: string) => Promise<void>;
}