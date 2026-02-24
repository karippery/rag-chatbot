import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthLayout } from '../components/AuthLayout';
import { PasswordInput } from '../components/PasswordInput';
import { authStyles as s } from '../styles/auth';
import { ui } from '../styles/ui';

export default function Signup() {
  const { signup, isLoading } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [confirm,  setConfirm]  = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [errors,   setErrors]   = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!fullName.trim())         e.fullName = 'Full name is required.';
    if (!email.trim())            e.email    = 'Email is required.';
    if (!password)                e.password = 'Password is required.';
    else if (password.length < 8) e.password = 'Minimum 8 characters.';
    if (password !== confirm)     e.confirm  = 'Passwords do not match.';
    return e;
  };

  const handleSubmit = async (e: SyntheticEvent) => {
    e.preventDefault();
    setApiError(null);
    const fe = validate();
    if (Object.keys(fe).length) { setErrors(fe); return; }
    setErrors({});
    try {
      await signup({ full_name: fullName, email, password });
      navigate('/');
    } catch (err: any) {
      const d = err.response?.data;
      if (d?.email)     setErrors(p => ({ ...p, email:    d.email[0] }));
      if (d?.password)  setErrors(p => ({ ...p, password: d.password[0] }));
      if (d?.full_name) setErrors(p => ({ ...p, fullName: d.full_name[0] }));
      if (d?.detail)    setApiError(d.detail);
    }
  };

  return (
    <AuthLayout>
      <div className={s.cardHeader}>
        <h1 className={s.cardTitle}>Create account</h1>
        <p className={s.cardSub}>Join your team's knowledge workspace</p>
      </div>

      <form onSubmit={handleSubmit} className={s.cardBody}>
        {apiError && (
          <div className={ui.alertError}><span>✕</span><span>{apiError}</span></div>
        )}

        <div className={ui.fieldWrap}>
          <label htmlFor="fullName" className={ui.label}>Full name</label>
          <input id="fullName" type="text" autoComplete="name" placeholder="Jane Smith"
                 value={fullName} onChange={e => setFullName(e.target.value)}
                 className={ui.input(!!errors.fullName)} />
          {errors.fullName && <span className={ui.fieldError}>{errors.fullName}</span>}
        </div>

        <div className={ui.fieldWrap}>
          <label htmlFor="email" className={ui.label}>Email</label>
          <input id="email" type="email" autoComplete="email" placeholder="you@company.com"
                 value={email} onChange={e => setEmail(e.target.value)}
                 className={ui.input(!!errors.email)} />
          {errors.email && <span className={ui.fieldError}>{errors.email}</span>}
        </div>

        <div className={ui.fieldWrap}>
          <label htmlFor="password" className={ui.label}>Password</label>
          <PasswordInput id="password" value={password} onChange={setPassword}
                         placeholder="Min. 8 characters" autoComplete="new-password"
                         hasError={!!errors.password} showStrength
                         showPw={showPw} onToggleShow={() => setShowPw(v => !v)} />
          {errors.password && <span className={ui.fieldError}>{errors.password}</span>}
        </div>

        <div className={ui.fieldWrap}>
          <label htmlFor="confirm" className={ui.label}>Confirm password</label>
          <PasswordInput id="confirm" value={confirm} onChange={setConfirm}
                         placeholder="Repeat password" autoComplete="new-password"
                         hasError={!!errors.confirm}
                         showPw={showPw} onToggleShow={() => setShowPw(v => !v)} />
          {errors.confirm && <span className={ui.fieldError}>{errors.confirm}</span>}
        </div>

        <button type="submit" disabled={isLoading} className={ui.btnPrimary}>
          {isLoading ? <><span className={ui.spinner} /> Creating…</> : 'Create account'}
        </button>
      </form>

      <div className={s.cardFooter}>
        Already have an account?{' '}
        <Link to="/login" className={ui.link}>Sign in</Link>
      </div>
    </AuthLayout>
  );
}