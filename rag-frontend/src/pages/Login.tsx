import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthLayout } from '../components/AuthLayout';
import { PasswordInput } from '../components/PasswordInput';
import { authStyles as s } from '../styles/auth';
import { ui } from '../styles/ui';

export default function Login() {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from     = (location.state as any)?.from?.pathname || '/';

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState<string | null>(null);

  const handleSubmit = async (e: SyntheticEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        'Invalid credentials.'
      );
    }
  };

  return (
    <AuthLayout>
      <div className={s.cardHeader}>
        <h1 className={s.cardTitle}>Welcome back</h1>
        <p className={s.cardSub}>Sign in to your account to continue</p>
      </div>

      <form onSubmit={handleSubmit} className={s.cardBody}>
        {error && (
          <div className={ui.alertError}>
            <span>✕</span><span>{error}</span>
          </div>
        )}

        <div className={ui.fieldWrap}>
          <label htmlFor="email" className={ui.label}>Email</label>
          <input id="email" type="email" required autoComplete="email"
                 value={email} onChange={e => setEmail(e.target.value)}
                 placeholder="you@company.com" className={ui.input()} />
        </div>

        <div className={ui.fieldWrap}>
          <div className={ui.fieldRow}>
            <label htmlFor="password" className={ui.label}>Password</label>
            <Link to="/forgot-password" className={ui.linkSm}>Forgot password?</Link>
          </div>
          <PasswordInput id="password" value={password} onChange={setPassword}
                         autoComplete="current-password" />
        </div>

        <button type="submit" disabled={isLoading} className={ui.btnPrimary}>
          {isLoading ? <><span className={ui.spinner} /> Signing in…</> : 'Sign in'}
        </button>
      </form>

      <div className={s.cardFooter}>
        Don't have an account?{' '}
        <Link to="/signup" className={ui.link}>Create one</Link>
      </div>
    </AuthLayout>
  );
}