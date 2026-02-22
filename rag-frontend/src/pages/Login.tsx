/**
 * src/pages/Login.tsx
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';

export default function Login() {
  const { login, isLoading } = useAuth();
  const navigate  = useNavigate();
  const location  = useLocation();
  const from      = (location.state as any)?.from?.pathname || '/';

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true }); // go back to where they came from
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        'Invalid credentials.';
      setError(msg);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#0d0f12] px-4"
         style={{
           backgroundImage: `
             linear-gradient(rgba(42,48,59,0.3) 1px, transparent 1px),
             linear-gradient(90deg, rgba(42,48,59,0.3) 1px, transparent 1px)
           `,
           backgroundSize: '48px 48px',
         }}>

      {/* Brand */}
      <div className="flex items-center gap-3 mb-10">
        <div className="w-9 h-9 rounded-xl border border-[#363d4a] bg-[#1a1e25] flex items-center justify-center text-[#4f8ef7]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div className="font-mono text-sm font-medium text-[#e2e6ed] tracking-widest">RAG</div>
          <div className="font-mono text-[10px] text-[#4f5a6a] tracking-wider">Knowledge Assistant</div>
        </div>
      </div>

      {/* Card */}
      <div className="w-full max-w-sm bg-[#13161b] border border-[#2a303b] rounded-2xl overflow-hidden">

        <div className="px-7 pt-7 pb-5 border-b border-[#2a303b]">
          <h1 className="text-lg font-medium text-[#e2e6ed]">Welcome back</h1>
          <p className="text-sm text-[#8b95a6] font-light mt-1">Sign in to your account to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="px-7 py-6 flex flex-col gap-4">

          {error && (
            <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-mono">
              <span className="mt-0.5">✕</span>
              <span>{error}</span>
            </div>
          )}

          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Email</label>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full px-3 py-2.5 bg-[#1a1e25] border border-[#2a303b] rounded-lg
                         text-sm text-[#e2e6ed] placeholder-[#4f5a6a]
                         focus:outline-none focus:border-[#4f8ef7] focus:ring-1 focus:ring-[#4f8ef7]/20
                         transition-colors"
            />
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Password</label>
              <Link to="/forgot-password" className="text-xs font-mono text-[#4f8ef7] hover:opacity-75 transition-opacity">
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                required
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2.5 pr-10 bg-[#1a1e25] border border-[#2a303b] rounded-lg
                           text-sm text-[#e2e6ed] placeholder-[#4f5a6a]
                           focus:outline-none focus:border-[#4f8ef7] focus:ring-1 focus:ring-[#4f8ef7]/20
                           transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPw(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#4f5a6a] hover:text-[#8b95a6] transition-colors"
              >
                {showPw
                  ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                }
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 mt-1 bg-[#4f8ef7] hover:opacity-85 disabled:opacity-40
                       rounded-lg text-white text-sm font-mono font-medium tracking-wide
                       transition-opacity flex items-center justify-center gap-2"
          >
            {isLoading
              ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Signing in…</>
              : 'Sign in'
            }
          </button>
        </form>

        <div className="px-7 py-4 border-t border-[#2a303b] text-center text-sm text-[#8b95a6]">
          Don't have an account?{' '}
          <Link to="/signup" className="text-[#4f8ef7] hover:opacity-75 transition-opacity">
            Create one
          </Link>
        </div>
      </div>
    </div>
  );
}