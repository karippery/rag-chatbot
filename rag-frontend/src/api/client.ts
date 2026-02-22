/**
 * src/api/client.ts
 *
 * Axios instance with:
 * - Automatic JWT attachment on every request
 * - Single-flight token refresh (queues concurrent 401s instead of
 *   firing multiple refresh calls simultaneously)
 * - Hard logout when refresh token is missing or expired
 */

import axios from 'axios';
import type { AxiosRequestConfig } from 'axios';

// ── Token storage helpers ──────────────────────────────────────────────────
// Centralised so switching to httpOnly cookies later only changes this file.

export const tokenStorage = {
  getAccess:      () => localStorage.getItem('access_token'),
  getRefresh:     () => localStorage.getItem('refresh_token'),
  setAccess:  (t: string) => localStorage.setItem('access_token', t),
  setRefresh: (t: string) => localStorage.setItem('refresh_token', t),
  clear: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// ── Axios instance ─────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: '/api',   // relative → Vite proxies to http://localhost:8000/api
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

// ── Request interceptor: attach access token ───────────────────────────────

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Refresh queue ──────────────────────────────────────────────────────────
// Prevents multiple simultaneous 401s from each triggering their own refresh.

let isRefreshing = false;
let refreshQueue: Array<{
  resolve: (token: string) => void;
  reject:  (err: unknown)  => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  refreshQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(token!)
  );
  refreshQueue = [];
}

// ── Response interceptor: handle 401 with single-flight refresh ────────────

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original: AxiosRequestConfig & { _retry?: boolean } = error.config;

    // Only intercept 401s that haven't already been retried
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    const refreshToken = tokenStorage.getRefresh();

    // No refresh token — user must log in again
    if (!refreshToken) {
      tokenStorage.clear();
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // If a refresh is already in flight, queue this request until it resolves
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshQueue.push({
          resolve: (token) => {
            original.headers = { ...original.headers, Authorization: `Bearer ${token}` };
            resolve(api(original));
          },
          reject,
        });
      });
    }

    original._retry = true;
    isRefreshing = true;

    try {
      const { data } = await axios.post(
        '/api/users/v1/token/refresh/',
        { refresh: refreshToken },
        { withCredentials: true }
      );

      const newAccess: string = data.access;
      tokenStorage.setAccess(newAccess);

      // Fulfil all queued requests with the new token
      processQueue(null, newAccess);

      original.headers = { ...original.headers, Authorization: `Bearer ${newAccess}` };
      return api(original);

    } catch (refreshError) {
      // Refresh token is invalid or expired — force logout
      processQueue(refreshError, null);
      tokenStorage.clear();
      window.location.href = '/login';
      return Promise.reject(refreshError);

    } finally {
      isRefreshing = false;
    }
  }
);

export default api;