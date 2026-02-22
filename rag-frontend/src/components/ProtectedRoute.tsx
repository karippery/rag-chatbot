/**
 * src/components/ProtectedRoute.tsx
 *
 * Wraps routes that require authentication.
 * Shows nothing while rehydrating (avoids flash of login page).
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Still checking stored token — render nothing to avoid flicker
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0d0f12]">
        <div className="w-6 h-6 border-2 border-[#4f8ef7] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    // Pass current location so login can redirect back after auth
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}