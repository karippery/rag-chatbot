/**
 * src/components/auth/PasswordInput.tsx
 */

import { useState } from 'react';
import { ui } from '../styles/ui';
import { strengthLevels } from '../styles/tokens';

interface PasswordInputProps {
  id:            string;
  value:         string;
  onChange:      (v: string) => void;
  placeholder?:  string;
  autoComplete?: string;
  hasError?:     boolean;
  showStrength?: boolean;
  showPw?:       boolean;
  onToggleShow?: () => void;
}

function getStrength(pw: string) {
  let score = 0;
  if (pw.length >= 8)                        score++;
  if (pw.length >= 12)                       score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw))                         score++;
  if (/[^A-Za-z0-9]/.test(pw))              score++;
  return strengthLevels[Math.min(score, 4)];
}

const EyeOpen = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
);
const EyeOff = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
  </svg>
);

export function PasswordInput({
  id, value, onChange,
  placeholder = '••••••••',
  autoComplete = 'current-password',
  hasError = false,
  showStrength = false,
  showPw: externalShow,
  onToggleShow,
}: PasswordInputProps) {
  const [internalShow, setInternalShow] = useState(false);
  const isVisible    = externalShow ?? internalShow;
  const handleToggle = onToggleShow ?? (() => setInternalShow(v => !v));
  const strength     = showStrength && value ? getStrength(value) : null;

  return (
    <div>
      <div className={ui.pwWrap}>
        <input
          id={id}
          type={isVisible ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className={ui.inputPw(hasError)}
        />
        <button type="button" onClick={handleToggle}
                className={ui.pwToggleBtn}
                aria-label={isVisible ? 'Hide password' : 'Show password'}>
          {isVisible ? <EyeOff /> : <EyeOpen />}
        </button>
      </div>
      {strength && (
        <div className={ui.strengthWrap}>
          <div className={ui.strengthTrack}>
            <div className={ui.strengthFill}
                 style={{ width: strength.pct, background: strength.color }} />
          </div>
          <span className={ui.strengthLabel} style={{ color: strength.color }}>
            {strength.label}
          </span>
        </div>
      )}
    </div>
  );
}