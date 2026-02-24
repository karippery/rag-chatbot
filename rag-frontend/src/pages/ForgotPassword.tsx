/**
 * src/pages/ForgotPassword.tsx
 * src/pages/ResetPassword.tsx
 */

import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthLayout } from '../components/AuthLayout';
import { PasswordInput } from '../components/PasswordInput';
import { authStyles as s } from '../styles/auth';
import { ui } from '../styles/ui';

// ── Forgot Password ────────────────────────────────────────────────────────

export function ForgotPassword() {
  const { forgotPassword } = useAuth();

  const [email,     setEmail]     = useState('');
  const [sent,      setSent]      = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: SyntheticEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await forgotPassword(email);
    } catch {
      // Never reveal if email exists — always show success
    } finally {
      setSent(true);
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className={s.cardHeader}>
        <h1 className={s.cardTitle}>Reset password</h1>
        <p className={s.cardSub}>We'll send a reset link to your email</p>
      </div>

      <div className={s.cardBody}>
        {sent ? (
          <div className={ui.alertSuccess}>
            <div className={ui.alertSuccessIcon}>✓</div>
            <p className="text-sm text-[#8b95a6] leading-relaxed">
              If that email is registered, a reset link is on its way. Check your inbox.
            </p>
            <Link to="/login" className={`${ui.linkSm} mt-2`}>
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className={ui.fieldWrap}>
              <label htmlFor="email" className={ui.label}>Email</label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className={ui.input()}
              />
            </div>
            <button type="submit" disabled={isLoading} className={ui.btnPrimary}>
              {isLoading
                ? <><span className={ui.spinner} /> Sending…</>
                : 'Send reset link'
              }
            </button>
          </form>
        )}
      </div>

      <div className={s.cardFooter}>
        Remembered it?{' '}
        <Link to="/login" className={ui.link}>Back to sign in</Link>
      </div>
    </AuthLayout>
  );
}

// ── Reset Password ─────────────────────────────────────────────────────────

export function ResetPassword() {
  const { uid = '', token = '' } = useParams<{ uid: string; token: string }>();
  const { resetPassword } = useAuth();
  const navigate = useNavigate();

  const [password,  setPassword]  = useState('');
  const [confirm,   setConfirm]   = useState('');
  const [showPw,    setShowPw]    = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error,     setError]     = useState<string | null>(null);

  const handleSubmit = async (e: SyntheticEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8)  { setError('Minimum 8 characters.'); return; }
    if (password !== confirm)  { setError('Passwords do not match.'); return; }

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
    <AuthLayout>
      <div className={s.cardHeader}>
        <h1 className={s.cardTitle}>Choose new password</h1>
        <p className={s.cardSub}>Pick something strong and memorable</p>
      </div>

      <form onSubmit={handleSubmit} className={s.cardBody}>
        {error && (
          <div className={ui.alertError}>
            <span className="mt-0.5">✕</span>
            <span>{error}</span>
          </div>
        )}

        <div className={ui.fieldWrap}>
          <label htmlFor="password" className={ui.label}>New password</label>
          <PasswordInput
            id="password"
            value={password}
            onChange={setPassword}
            placeholder="Min. 8 characters"
            autoComplete="new-password"
            showStrength
            showPw={showPw}
            onToggleShow={() => setShowPw(v => !v)}
          />
        </div>

        <div className={ui.fieldWrap}>
          <label htmlFor="confirm" className={ui.label}>Confirm password</label>
          <PasswordInput
            id="confirm"
            value={confirm}
            onChange={setConfirm}
            placeholder="Repeat password"
            autoComplete="new-password"
            showPw={showPw}
            onToggleShow={() => setShowPw(v => !v)}
          />
        </div>

        <button type="submit" disabled={isLoading} className={ui.btnPrimary}>
          {isLoading
            ? <><span className={ui.spinner} /> Setting…</>
            : 'Set new password'
          }
        </button>
      </form>

      <div className={s.cardFooter}>
        <Link to="/login" className={ui.link}>Back to sign in</Link>
      </div>
    </AuthLayout>
  );
}