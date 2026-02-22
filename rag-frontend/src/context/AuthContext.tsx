/**
 * src/context/AuthContext.tsx
 *
 * Decodes user info directly from the JWT payload instead of calling /me/.
 * This avoids needing a separate profile endpoint while still rehydrating
 * user state correctly on page refresh.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';
import type { ReactNode } from 'react';

import api, { tokenStorage } from '../api/client';
import type { User, AuthContextType, SignupPayload } from '../types/auth';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ── JWT helpers ────────────────────────────────────────────────────────────

interface JWTPayload {
  user_id:    string;
  exp:        number;
  token_type: string;
}

function decodeToken(token: string): JWTPayload | null {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload)) as JWTPayload;
  } catch {
    return null;
  }
}

function isTokenValid(token: string | null): boolean {
  if (!token) return false;
  const decoded = decodeToken(token);
  if (!decoded?.exp) return false;
  return decoded.exp * 1000 > Date.now() + 10_000;
}

function userFromToken(token: string, extra: Partial<User> = {}): User {
  const decoded = decodeToken(token);
  return {
    id:        parseInt(decoded?.user_id ?? '0'),
    email:     extra.email     ?? '',
    full_name: extra.full_name ?? '',
    role:      extra.role      ?? '',
    is_active: true,
    ...extra,
  };
}

// ── Provider ───────────────────────────────────────────────────────────────

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user,      setUser]      = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ── Rehydrate on page refresh ────────────────────────────────────────────
  useEffect(() => {
    const token = tokenStorage.getAccess();
    if (!isTokenValid(token)) {
      tokenStorage.clear();
      setIsLoading(false);
      return;
    }
    setUser(userFromToken(token!));
    setIsLoading(false);
  }, []);

  // ── Login ────────────────────────────────────────────────────────────────
  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post('/users/v1/login/', { email, password });
    tokenStorage.setAccess(data.access);
    tokenStorage.setRefresh(data.refresh);
    setUser(userFromToken(data.access, { email }));
  }, []);

  // ── Signup ───────────────────────────────────────────────────────────────
  const signup = useCallback(async (payload: SignupPayload) => {
    await api.post('/users/v1/', payload);
    await login(payload.email, payload.password);
  }, [login]);

  // ── Logout ───────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
  }, []);

  // ── Forgot password ──────────────────────────────────────────────────────
  const forgotPassword = useCallback(async (email: string) => {
    await api.post('/users/v1/password-reset/', { email });
  }, []);

  // ── Reset password ───────────────────────────────────────────────────────
  const resetPassword = useCallback(
    async (uid: string, token: string, newPassword: string) => {
      await api.post('/users/v1/password-reset-confirm/', {
        uid,
        token,
        new_password: newPassword,
      });
    },
    []
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
        forgotPassword,
        resetPassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// ── Hook ───────────────────────────────────────────────────────────────────

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within <AuthProvider>');
  return context;
};