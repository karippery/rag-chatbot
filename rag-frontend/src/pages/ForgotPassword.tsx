/**
 * src/pages/ForgotPassword.tsx
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';

export function ForgotPassword() {
  const { forgotPassword } = useAuth();
  const [email,     setEmail]     = useState('');
  const [sent,      setSent]      = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error,     setError]     = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch {
      // Never reveal if email exists — always show success
      setSent(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#0d0f12] px-4"
         style={{
           backgroundImage: `linear-gradient(rgba(42,48,59,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(42,48,59,0.3) 1px, transparent 1px)`,
           backgroundSize: '48px 48px',
         }}>

      <div className="flex items-center gap-3 mb-10">
        <div className="w-9 h-9 rounded-xl border border-[#363d4a] bg-[#1a1e25] flex items-center justify-center text-[#4f8ef7]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div className="font-mono text-sm font-medium text-[#e2e6ed] tracking-widest">RAG</div>
          <div className="font-mono text-[10px] text-[#4f5a6a] tracking-wider">Knowledge Assistant</div>
        </div>
      </div>

      <div className="w-full max-w-sm bg-[#13161b] border border-[#2a303b] rounded-2xl overflow-hidden">
        <div className="px-7 pt-7 pb-5 border-b border-[#2a303b]">
          <h1 className="text-lg font-medium text-[#e2e6ed]">Reset password</h1>
          <p className="text-sm text-[#8b95a6] font-light mt-1">We'll send a reset link to your email</p>
        </div>

        <div className="px-7 py-6">
          {sent ? (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <div className="w-10 h-10 rounded-full bg-[#3ecf8e]/10 border border-[#3ecf8e]/25 flex items-center justify-center text-[#3ecf8e]">
                ✓
              </div>
              <p className="text-sm text-[#8b95a6] leading-relaxed">
                If that email is registered, a reset link is on its way.
                Check your inbox.
              </p>
              <Link to="/login" className="text-sm font-mono text-[#4f8ef7] hover:opacity-75 transition-opacity mt-2">
                Back to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {error && (
                <div className="px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-mono">
                  {error}
                </div>
              )}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Email</label>
                <input type="email" required placeholder="you@company.com" autoComplete="email"
                       value={email} onChange={e => setEmail(e.target.value)}
                       className="w-full px-3 py-2.5 bg-[#1a1e25] border border-[#2a303b] rounded-lg
                                  text-sm text-[#e2e6ed] placeholder-[#4f5a6a]
                                  focus:outline-none focus:border-[#4f8ef7] focus:ring-1 focus:ring-[#4f8ef7]/20 transition-colors" />
              </div>
              <button type="submit" disabled={isLoading}
                      className="w-full py-2.5 bg-[#4f8ef7] hover:opacity-85 disabled:opacity-40 rounded-lg
                                 text-white text-sm font-mono font-medium tracking-wide transition-opacity
                                 flex items-center justify-center gap-2">
                {isLoading
                  ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Sending…</>
                  : 'Send reset link'
                }
              </button>
            </form>
          )}
        </div>

        <div className="px-7 py-4 border-t border-[#2a303b] text-center text-sm text-[#8b95a6]">
          Remembered it?{' '}
          <Link to="/login" className="text-[#4f8ef7] hover:opacity-75 transition-opacity">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}


/**
 * src/pages/ResetPassword.tsx
 *
 * Reads uid + token from URL params: /reset-password/:uid/:token
 */

import { useParams, useNavigate } from 'react-router-dom';

export function ResetPassword() {
  const { uid = '', token = '' } = useParams<{ uid: string; token: string }>();
  const { resetPassword } = useAuth();
  const navigate = useNavigate();

  const [password,  setPassword]  = useState('');
  const [confirm,   setConfirm]   = useState('');
  const [showPw,    setShowPw]    = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error,     setError]     = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) { setError('Minimum 8 characters.'); return; }
    if (password !== confirm) { setError('Passwords do not match.'); return; }

    setIsLoading(true);
    try {
      await resetPassword(uid, token, password);
      navigate('/login', { state: { resetSuccess: true } });
    } catch (err: any) {
      const data = err.response?.data;
      setError(
        data?.new_password?.[0] ||
        data?.non_field_errors?.[0] ||
        data?.detail ||
        'Invalid or expired link.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#0d0f12] px-4"
         style={{
           backgroundImage: `linear-gradient(rgba(42,48,59,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(42,48,59,0.3) 1px, transparent 1px)`,
           backgroundSize: '48px 48px',
         }}>

      <div className="flex items-center gap-3 mb-10">
        <div className="w-9 h-9 rounded-xl border border-[#363d4a] bg-[#1a1e25] flex items-center justify-center text-[#4f8ef7]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div className="font-mono text-sm font-medium text-[#e2e6ed] tracking-widest">RAG</div>
          <div className="font-mono text-[10px] text-[#4f5a6a] tracking-wider">Knowledge Assistant</div>
        </div>
      </div>

      <div className="w-full max-w-sm bg-[#13161b] border border-[#2a303b] rounded-2xl overflow-hidden">
        <div className="px-7 pt-7 pb-5 border-b border-[#2a303b]">
          <h1 className="text-lg font-medium text-[#e2e6ed]">Choose new password</h1>
          <p className="text-sm text-[#8b95a6] font-light mt-1">Pick something strong and memorable</p>
        </div>

        <form onSubmit={handleSubmit} className="px-7 py-6 flex flex-col gap-4">
          {error && (
            <div className="px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-mono">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-mono text-[#8b95a6] tracking-wide">New password</label>
            <div className="relative">
              <input type={showPw ? 'text' : 'password'} required placeholder="Min. 8 characters"
                     autoComplete="new-password" value={password}
                     onChange={e => setPassword(e.target.value)}
                     className="w-full px-3 py-2.5 pr-10 bg-[#1a1e25] border border-[#2a303b] rounded-lg
                                text-sm text-[#e2e6ed] placeholder-[#4f5a6a]
                                focus:outline-none focus:border-[#4f8ef7] focus:ring-1 focus:ring-[#4f8ef7]/20 transition-colors" />
              <button type="button" onClick={() => setShowPw(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#4f5a6a] hover:text-[#8b95a6] transition-colors">
                {showPw
                  ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                }
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Confirm password</label>
            <input type={showPw ? 'text' : 'password'} required placeholder="Repeat password"
                   autoComplete="new-password" value={confirm}
                   onChange={e => setConfirm(e.target.value)}
                   className="w-full px-3 py-2.5 bg-[#1a1e25] border border-[#2a303b] rounded-lg
                              text-sm text-[#e2e6ed] placeholder-[#4f5a6a]
                              focus:outline-none focus:border-[#4f8ef7] focus:ring-1 focus:ring-[#4f8ef7]/20 transition-colors" />
          </div>

          <button type="submit" disabled={isLoading}
                  className="w-full py-2.5 mt-1 bg-[#4f8ef7] hover:opacity-85 disabled:opacity-40 rounded-lg
                             text-white text-sm font-mono font-medium tracking-wide transition-opacity
                             flex items-center justify-center gap-2">
            {isLoading
              ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Setting…</>
              : 'Set new password'
            }
          </button>
        </form>

        <div className="px-7 py-4 border-t border-[#2a303b] text-center text-sm text-[#8b95a6]">
          <Link to="/login" className="text-[#4f8ef7] hover:opacity-75 transition-opacity">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}