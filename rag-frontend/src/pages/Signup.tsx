/**
 * src/pages/Signup.tsx
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

function getStrength(pw: string): { label: string; color: string; pct: string } {
  let score = 0;
  if (pw.length >= 8)                        score++;
  if (pw.length >= 12)                       score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw))                         score++;
  if (/[^A-Za-z0-9]/.test(pw))              score++;
  const levels = [
    { label: 'Very weak',   color: '#f56565', pct: '20%' },
    { label: 'Weak',        color: '#f5a623', pct: '40%' },
    { label: 'Fair',        color: '#ecc94b', pct: '60%' },
    { label: 'Strong',      color: '#4f8ef7', pct: '80%' },
    { label: 'Very strong', color: '#3ecf8e', pct: '100%' },
  ];
  return levels[Math.min(score, 4)];
}

export default function Signup() {
  const { signup, isLoading } = useAuth();
  const navigate = useNavigate();

  const [fullName,  setFullName]  = useState('');
  const [email,     setEmail]     = useState('');
  const [password,  setPassword]  = useState('');
  const [confirm,   setConfirm]   = useState('');
  const [showPw,    setShowPw]    = useState(false);
  const [errors,    setErrors]    = useState<Record<string, string>>({});
  const [apiError,  setApiError]  = useState<string | null>(null);

  const strength = password ? getStrength(password) : null;

  const validate = () => {
    const e: Record<string, string> = {};
    if (!fullName.trim())    e.fullName = 'Full name is required.';
    if (!email.trim())       e.email    = 'Email is required.';
    if (!password)           e.password = 'Password is required.';
    else if (password.length < 8) e.password = 'Minimum 8 characters.';
    if (password !== confirm) e.confirm  = 'Passwords do not match.';
    return e;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const fieldErrors = validate();
    if (Object.keys(fieldErrors).length) { setErrors(fieldErrors); return; }
    setErrors({});

    try {
      await signup({ full_name: fullName, email, password });
      navigate('/');
    } catch (err: any) {
      const data = err.response?.data;
      if (data?.email)     setErrors(prev => ({ ...prev, email:    data.email[0] }));
      if (data?.password)  setErrors(prev => ({ ...prev, password: data.password[0] }));
      if (data?.full_name) setErrors(prev => ({ ...prev, fullName: data.full_name[0] }));
      if (data?.detail)    setApiError(data.detail);
    }
  };

  const inputCls = (field: string) => `
    w-full px-3 py-2.5 bg-[#1a1e25] border rounded-lg text-sm text-[#e2e6ed]
    placeholder-[#4f5a6a] focus:outline-none transition-colors
    ${errors[field]
      ? 'border-red-500/60 focus:border-red-500 focus:ring-1 focus:ring-red-500/20'
      : 'border-[#2a303b] focus:border-[#4f8ef7] focus:ring-1 focus:ring-[#4f8ef7]/20'}
  `;

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

      <div className="w-full max-w-sm bg-[#13161b] border border-[#2a303b] rounded-2xl overflow-hidden">

        <div className="px-7 pt-7 pb-5 border-b border-[#2a303b]">
          <h1 className="text-lg font-medium text-[#e2e6ed]">Create account</h1>
          <p className="text-sm text-[#8b95a6] font-light mt-1">Join your team's knowledge workspace</p>
        </div>

        <form onSubmit={handleSubmit} className="px-7 py-6 flex flex-col gap-4">

          {apiError && (
            <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-mono">
              <span className="mt-0.5">✕</span><span>{apiError}</span>
            </div>
          )}

          {/* Full name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Full name</label>
            <input type="text" placeholder="Jane Smith" autoComplete="name"
                   value={fullName} onChange={e => setFullName(e.target.value)}
                   className={inputCls('fullName')} />
            {errors.fullName && <span className="text-xs font-mono text-red-400">{errors.fullName}</span>}
          </div>

          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Email</label>
            <input type="email" placeholder="you@company.com" autoComplete="email"
                   value={email} onChange={e => setEmail(e.target.value)}
                   className={inputCls('email')} />
            {errors.email && <span className="text-xs font-mono text-red-400">{errors.email}</span>}
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Password</label>
            <div className="relative">
              <input type={showPw ? 'text' : 'password'} placeholder="Min. 8 characters"
                     autoComplete="new-password" value={password}
                     onChange={e => setPassword(e.target.value)}
                     className={inputCls('password') + ' pr-10'} />
              <button type="button" onClick={() => setShowPw(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#4f5a6a] hover:text-[#8b95a6] transition-colors">
                {showPw
                  ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                }
              </button>
            </div>
            {/* Strength bar */}
            {strength && (
              <div className="flex flex-col gap-1 mt-1">
                <div className="h-0.5 rounded-full bg-[#21262f] overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-300"
                       style={{ width: strength.pct, background: strength.color }} />
                </div>
                <span className="text-[10px] font-mono" style={{ color: strength.color }}>
                  {strength.label}
                </span>
              </div>
            )}
            {errors.password && <span className="text-xs font-mono text-red-400">{errors.password}</span>}
          </div>

          {/* Confirm */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-mono text-[#8b95a6] tracking-wide">Confirm password</label>
            <input type={showPw ? 'text' : 'password'} placeholder="Repeat password"
                   autoComplete="new-password" value={confirm}
                   onChange={e => setConfirm(e.target.value)}
                   className={inputCls('confirm')} />
            {errors.confirm && <span className="text-xs font-mono text-red-400">{errors.confirm}</span>}
          </div>

          <button type="submit" disabled={isLoading}
                  className="w-full py-2.5 mt-1 bg-[#4f8ef7] hover:opacity-85 disabled:opacity-40
                             rounded-lg text-white text-sm font-mono font-medium tracking-wide
                             transition-opacity flex items-center justify-center gap-2">
            {isLoading
              ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Creating…</>
              : 'Create account'
            }
          </button>
        </form>

        <div className="px-7 py-4 border-t border-[#2a303b] text-center text-sm text-[#8b95a6]">
          Already have an account?{' '}
          <Link to="/login" className="text-[#4f8ef7] hover:opacity-75 transition-opacity">Sign in</Link>
        </div>
      </div>
    </div>
  );
}